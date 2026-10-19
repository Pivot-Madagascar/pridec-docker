import logging
import time
from urllib.parse import urlparse

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr

from etlhub.api.auth.dhis2_auth import (
    _LOCAL_HOSTS,
    allowed_hosts,
    SESSION_COOKIE,
    TOKEN_LIFETIME_SECONDS,
    DHIS2Error,
    create_pat,
    dhis2_client,
    fetch_me,
    get_current_user,
    normalize_dhis2_url,
    revoke_pat,
)
from etlhub.api.routers import NOT_AUTHENTICATED, error_doc
from etlhub.core.config import get_settings
from etlhub.infrastructure import auth_store
from etlhub.infrastructure.config_store import ConfigStore

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["Authentication"])

MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60

# Documented with examples, not response_model: a model would filter the user dict etlui reads.
_USER = {"id": "xE7jOejl9FI", "email": None, "username": "admin", "displayName": "John Traore", "is_admin": True}


class LoginRequest(BaseModel):
    dhis2_url: str = Field(min_length=1, max_length=2048)
    username: str = Field(min_length=1, max_length=255)
    password: SecretStr = Field(min_length=1, max_length=1024)


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=TOKEN_LIFETIME_SECONDS,
        httponly=True,
        samesite="strict",
        secure=get_settings().cookie_secure,
        path="/",
    )


def _revoke_previous(client: httpx.Client, url: str, basic: tuple) -> None:
    """Revoke the token etlhub created at the previous login, and only that one."""
    previous = auth_store.get_credential()
    if not previous:
        return
    revoked = revoke_pat(client, previous["url"], previous["pat_uid"], token=previous["token"])
    if not revoked and previous["url"] == url:
        revoke_pat(client, url, previous["pat_uid"], auth=basic)
    # Never leave a revoked token where jobs and sessions would still use it,
    # even if creating the new one fails below.
    auth_store.delete_credential()


def _rollback(client: httpx.Client, url: str, uid: str, basic: tuple) -> None:
    revoke_pat(client, url, uid, auth=basic)
    try:
        current = auth_store.get_credential()
        if current and current["pat_uid"] == uid:
            auth_store.delete_credential()
    except redis.RedisError as e:
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
def login(body: LoginRequest, request: Request, response: Response):
    """Log in with a DHIS2 username and password.

    etlhub creates a 24h DHIS2 personal access token for this user, stores it in Redis
    for the ETL jobs, revokes the one created at the previous login, and sets an
    HttpOnly session cookie. The password is neither stored nor logged.
    """
    url = normalize_dhis2_url(body.dhis2_url)
    if not url:
        raise HTTPException(status_code=400, detail="DHIS2 URL not allowed")

    ip = request.client.host if request.client else "unknown"
    try:
        if auth_store.failed_logins(ip, body.username) >= MAX_FAILED_LOGINS:
            raise HTTPException(status_code=429, detail="Too many failed attempts, try again later")

        basic = (body.username, body.password.get_secret_value())
        with dhis2_client() as client:
            user = fetch_me(client, url, auth=basic)
            if user is None:
                auth_store.record_failed_login(ip, body.username, FAILED_LOGIN_WINDOW_SECONDS)
                raise HTTPException(status_code=401, detail="Invalid DHIS2 username or password")
            auth_store.clear_failed_logins(ip, body.username)

            _revoke_previous(client, url, basic)
            expires_at = int(time.time()) + TOKEN_LIFETIME_SECONDS
            key, uid = create_pat(client, url, basic, expires_at * 1000)
            try:
                if fetch_me(client, url, token=key) is None:
                    raise DHIS2Error("DHIS2 rejected the token it just created")
                auth_store.set_credential(
                    {"url": url, "token": key, "pat_uid": uid, "username": user["username"], "expires_at": expires_at},
                    ttl=TOKEN_LIFETIME_SECONDS,
                )
                session_id = auth_store.create_session(user, uid, TOKEN_LIFETIME_SECONDS)
                # Values written by the old config form; nothing reads them any more.
                ConfigStore().delete_keys(["DHIS_URL", "DHIS_TOKEN"])
            except Exception:
                _rollback(client, url, uid, basic)
                raise
    except (DHIS2Error, httpx.HTTPError) as e:
        logger.warning("DHIS2 login failed for user=%s url=%s: %s", body.username, url, e)
        raise HTTPException(status_code=502, detail="DHIS2 unreachable or returned an unexpected response")
    except redis.RedisError as e:
        logger.error("DHIS2 login failed for user=%s: Redis error: %s", body.username, e)
        raise HTTPException(status_code=503, detail="Session store unavailable")

    _set_session_cookie(response, session_id)
    logger.info("DHIS2 login: user=%s url=%s ip=%s token_uid=%s", body.username, url, ip, uid)
    return {"user": user, "expires_at": expires_at}


@auth_router.post("/auth/logout", status_code=204, summary="Log out")
def logout(request: Request):
    """End the session and revoke its DHIS2 token. Always clears the cookie."""
    session_id = request.cookies.get(SESSION_COOKIE)
    session = auth_store.get_session(session_id) if session_id else None
    if session:
        auth_store.delete_session(session_id)
        credential = auth_store.get_credential()
        if credential and credential["pat_uid"] == session["pat_uid"]:
            with dhis2_client() as client:
                revoke_pat(client, credential["url"], credential["pat_uid"], token=credential["token"])
            auth_store.delete_credential()
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
