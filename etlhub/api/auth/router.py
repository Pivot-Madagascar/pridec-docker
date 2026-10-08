import logging
import time

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr

from etlhub.api.auth.dhis2_auth import (
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
from etlhub.core.config import get_settings
from etlhub.infrastructure import auth_store
from etlhub.infrastructure.config_store import ConfigStore

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["Authentication"])

MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60


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


def _rollback(client: httpx.Client, url: str, uid: str, basic: tuple) -> None:
    revoke_pat(client, url, uid, auth=basic)
    try:
        current = auth_store.get_credential()
        if current and current["pat_uid"] == uid:
            auth_store.delete_credential()
    except redis.RedisError as e:
        logger.error("Could not remove the revoked DHIS2 credential from Redis: %s", e)


@auth_router.post("/auth/login")
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


@auth_router.post("/auth/logout", status_code=204)
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


@auth_router.get("/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    """Current user, while the session and its DHIS2 token are valid."""
    return user
