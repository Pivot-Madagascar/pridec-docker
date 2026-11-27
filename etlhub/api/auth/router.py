import hashlib
import logging
import secrets
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr

from etlhub.api.auth.dhis2_auth import (
    _LOCAL_HOSTS,
    DEVICE_COOKIE,
    allowed_hosts,
    SESSION_COOKIE,
    SESSION_LIFETIME_SECONDS,
    TOKEN_LIFETIME_SECONDS,
    get_current_user,
    normalize_dhis2_url,
)
from etlhub.api.routers import NOT_AUTHENTICATED, error_doc
from etlhub.core.config import get_settings
from etlhub.core.dependencies import get_auth_store, get_config_store, get_dhis2_accounts, get_pipeline_gate
from etlhub.domain.exceptions import AuthStoreUnavailable, DHIS2Error
from etlhub.domain.interfaces.dhis2_accounts import DHIS2Accounts

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["Authentication"])

MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60

# Documented with examples, not response_model: a model would filter the user dict etlui reads.
_USER = {"id": "xE7jOejl9FI", "email": None, "username": "admin", "displayName": "John Traore"}


class LoginRequest(BaseModel):
    dhis2_url: str = Field(min_length=1, max_length=2048)
    username: str = Field(min_length=1, max_length=255)
    password: SecretStr = Field(min_length=1, max_length=1024)


def _set_cookie(response: Response, name: str, value: str, max_age: int) -> None:
    response.set_cookie(name, value, max_age=max_age, httponly=True, samesite="strict",
                        secure=get_settings().cookie_secure, path="/")


def _device_hash(device_id: str) -> str:
    return hashlib.sha256(device_id.encode()).hexdigest()


def _job_running() -> bool:
    """A job holding the pipeline lock read the DHIS2 token once, at its start: revoking it would stop it half done.

    Its token is then left to expire on its own (30 days at most). Unreadable gate: kept too, the safe side."""
    try:
        return get_pipeline_gate().progress()["lock"] is not None
    except Exception as e:
        logger.warning("Could not read the pipeline lock, the previous DHIS2 token is kept: %s", e)
        return True


def _revoke(dhis2: DHIS2Accounts, previous: dict, url: str | None = None, basic: tuple | None = None) -> None:
    """Revoke an account's token and forget it (not revoked while a job runs: it may use it; it then expires alone)."""
    if _job_running():
        logger.info("DHIS2 token uid=%s not revoked: a job is running, it expires on its own", previous["pat_uid"])
    else:
        revoked = dhis2.revoke_pat(previous["url"], previous["pat_uid"], token=previous["token"])
        if not revoked and basic and previous["url"] == url:
            dhis2.revoke_pat(url, previous["pat_uid"], auth=basic)
    # Never leave a revoked token where jobs and sessions would still use it,
    # even if creating the new one fails below.
    get_auth_store().delete_credential(previous["username"])


def _reusable(dhis2: DHIS2Accounts, current: dict | None, url: str, device_id: str | None) -> bool:
    """The account's token is kept when this browser created it, on this DHIS2, and DHIS2 still accepts it."""
    return bool(current and device_id and current["url"] == url and current.get("device") == _device_hash(device_id)
                and dhis2.fetch_me(url, token=current["token"]) is not None)


def _rollback(dhis2: DHIS2Accounts, url: str, uid: str, basic: tuple, username: str) -> None:
    dhis2.revoke_pat(url, uid, auth=basic)
    try:
        current = get_auth_store().get_credential(username)
        if current and current["pat_uid"] == uid:
            get_auth_store().delete_credential(username)
    except AuthStoreUnavailable as e:
        logger.error("Could not remove the revoked DHIS2 credential from Redis: %s", e)


@auth_router.get(
    "/auth/dhis2-urls",
    summary="DHIS2 URLs the login accepts",
    responses={200: {"content": {"application/json": {"example": ["http://localhost:8082", "https://dhis2.example.org"]}}}},
)
def dhis2_urls() -> list[str]:
    """URLs built from DHIS2_ALLOWED_HOSTS, for the login form to suggest.

    Public: the login page needs them before any session. http for localhost, https
    otherwise, the same rule as POST /auth/login.
    """
    return [f"{'http' if urlparse('//' + h).hostname in _LOCAL_HOSTS else 'https'}://{h}" for h in allowed_hosts()]


@auth_router.post(
    "/auth/login",
    summary="Log in with DHIS2 credentials",
    responses={
        200: {"content": {"application/json": {"example": {"user": _USER, "expires_at": 1792137600}}}},
        400: error_doc("dhis2_url refused: host not in DHIS2_ALLOWED_HOSTS, plain http outside localhost, "
                       "or credentials, query or fragment in the URL",
                       {"detail": "DHIS2 URL not allowed"}),
        401: error_doc("DHIS2 rejected the username or password", {"detail": "Invalid DHIS2 username or password"}),
        429: error_doc(f"{MAX_FAILED_LOGINS} failures for this IP and username in the last "
                       f"{FAILED_LOGIN_WINDOW_SECONDS // 60} minutes",
                       {"detail": "Too many failed attempts, try again later"}),
        502: error_doc("DHIS2 unreachable or unexpected answer",
                       {"detail": "DHIS2 unreachable or returned an unexpected response"}),
        503: error_doc("Redis unavailable", {"detail": "Session store unavailable"}),
    },
)
def login(body: LoginRequest, request: Request, response: Response,
          accounts: DHIS2Accounts = Depends(get_dhis2_accounts)):
    """Log in with a DHIS2 username and password.

    One DHIS2 personal access token per account, 30 days; the session (HttpOnly cookie) lasts 24 h. A login from the
    browser that created the account's token reuses it while DHIS2 accepts it (browser told by the `etlhub_device`
    cookie). Otherwise etlhub revokes that account's token, which logs its other browser out (not revoked while a job
    runs: it may use it), and creates a new one. Other accounts keep theirs. The ETL jobs use the most recently created
    token. The password is neither stored nor logged.
    """
    url = normalize_dhis2_url(body.dhis2_url)
    if not url:
        raise HTTPException(status_code=400, detail="DHIS2 URL not allowed")

    ip = request.client.host if request.client else "unknown"
    try:
        if get_auth_store().failed_logins(ip, body.username) >= MAX_FAILED_LOGINS:
            raise HTTPException(status_code=429, detail="Too many failed attempts, try again later")

        basic = (body.username, body.password.get_secret_value())
        with accounts as dhis2:
            user = dhis2.fetch_me(url, auth=basic)
            if user is None:
                get_auth_store().record_failed_login(ip, body.username, FAILED_LOGIN_WINDOW_SECONDS)
                raise HTTPException(status_code=401, detail="Invalid DHIS2 username or password")
            get_auth_store().clear_failed_logins(ip, body.username)

            username = user["username"]
            current = get_auth_store().get_credential(username)  # gone once its 30 days are over (Redis TTL)
            device_id = request.cookies.get(DEVICE_COOKIE)
            if _reusable(dhis2, current, url, device_id):
                session_id = get_auth_store().create_session(user, current["pat_uid"], SESSION_LIFETIME_SECONDS)
                _set_cookie(response, SESSION_COOKIE, session_id, SESSION_LIFETIME_SECONDS)
                logger.info("DHIS2 login: user=%s url=%s ip=%s token_uid=%s (kept)", username, url, ip,
                            current["pat_uid"])
                return {"user": user, "expires_at": current["expires_at"]}

            # Another browser, another DHIS2, or a token DHIS2 no longer accepts: this account's token is replaced.
            if current:
                _revoke(dhis2, current, url, basic)
            device_id = device_id or secrets.token_urlsafe(32)
            expires_at = int(time.time()) + TOKEN_LIFETIME_SECONDS
            key, uid = dhis2.create_pat(url, basic, expires_at * 1000)
            try:
                if dhis2.fetch_me(url, token=key) is None:
                    raise DHIS2Error("DHIS2 rejected the token it just created")
                get_auth_store().set_credential(
                    {"url": url, "token": key, "pat_uid": uid, "username": username, "expires_at": expires_at,
                     "created_at": time.time(), "device": _device_hash(device_id)},
                    ttl=TOKEN_LIFETIME_SECONDS,
                )
                session_id = get_auth_store().create_session(user, uid, SESSION_LIFETIME_SECONDS)
                # Values written by the old config form; nothing reads them any more.
                get_config_store().delete_keys(["DHIS_URL", "DHIS_TOKEN"])
            except Exception:
                _rollback(dhis2, url, uid, basic, username)
                raise
    except DHIS2Error as e:
        logger.warning("DHIS2 login failed for user=%s url=%s: %s", body.username, url, e)
        raise HTTPException(status_code=502, detail="DHIS2 unreachable or returned an unexpected response")
    except AuthStoreUnavailable as e:
        logger.error("DHIS2 login failed for user=%s: Redis error: %s", body.username, e)
        raise HTTPException(status_code=503, detail="Session store unavailable")

    _set_cookie(response, SESSION_COOKIE, session_id, SESSION_LIFETIME_SECONDS)
    _set_cookie(response, DEVICE_COOKIE, device_id, TOKEN_LIFETIME_SECONDS)
    logger.info("DHIS2 login: user=%s url=%s ip=%s token_uid=%s", body.username, url, ip, uid)
    return {"user": user, "expires_at": expires_at}


@auth_router.post("/auth/logout", status_code=204, summary="Log out")
def logout(request: Request, accounts: DHIS2Accounts = Depends(get_dhis2_accounts)):
    """End the session and revoke its account's DHIS2 token (not while a job runs: it may use it). Other accounts keep
    theirs. Always clears the session cookie."""
    session_id = request.cookies.get(SESSION_COOKIE)
    session = get_auth_store().get_session(session_id) if session_id else None
    if session:
        get_auth_store().delete_session(session_id)
        credential = get_auth_store().get_credential(session["user"]["username"])
        if credential and credential["pat_uid"] == session["pat_uid"]:
            with accounts as dhis2:
                _revoke(dhis2, credential)
        logger.info("DHIS2 logout: user=%s", session["user"].get("username"))

    response = Response(status_code=204)
    response.delete_cookie(
        SESSION_COOKIE, path="/", httponly=True, samesite="strict", secure=get_settings().cookie_secure
    )
    return response


@auth_router.get(
    "/auth/me",
    summary="Current user",
    responses={
        200: {"content": {"application/json": {"example": _USER}}},
        **NOT_AUTHENTICATED,
    },
)
def get_me(user: dict = Depends(get_current_user)):
    """Current user, while the session and its DHIS2 token are valid."""
    return user
