"""DHIS2 calls used by login/logout, and the session dependency.

Login exchanges a DHIS2 username/password for a personal access token (PAT). The PAT
never leaves the server: the browser only gets an HttpOnly session cookie.
"""
import logging
import re
from urllib.parse import urlparse

import httpx
from fastapi import Depends, HTTPException, WebSocketException, status
from starlette.concurrency import run_in_threadpool
from starlette.requests import HTTPConnection

from etlhub.api.middleware import is_allowed_origin
from etlhub.core.config import get_settings
from etlhub.infrastructure import auth_store

logger = logging.getLogger(__name__)

SESSION_COOKIE = "etlhub_session"
# WebSocket close code when the session is missing or no longer valid. etlui sends the
# user back to /login on it (useWebSocketLogger.ts).
WS_NOT_AUTHENTICATED = 4401
TOKEN_LIFETIME_SECONDS = 24 * 3600

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_UID = re.compile(r"^[A-Za-z0-9]{11}$")
# Attributes DHIS2 2.40 requires to create a PAT (checked manually against 2.40.3).
_PAT_ATTRIBUTES = [{"type": "MethodAllowedList", "allowedMethods": ["GET", "POST", "PUT", "PATCH", "DELETE"]}]


class DHIS2Error(Exception):
    """DHIS2 is unreachable or answered something unexpected."""


def normalize_dhis2_url(url: str) -> str | None:
    """Return the URL without trailing slash if it may receive credentials, else None.

    The host must be listed in DHIS2_ALLOWED_HOSTS (an empty list refuses everything),
    and plain http is accepted for localhost only.
    """
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    if parsed.scheme == "http" and parsed.hostname not in _LOCAL_HOSTS:
        return None
    allowed = {h.strip().lower() for h in get_settings().dhis2_allowed_hosts.split(",") if h.strip()}
    if parsed.netloc.lower() not in allowed:
        return None
    return url.strip().rstrip("/")


def dhis2_client() -> httpx.Client:
    # No redirects: credentials must only ever go to the allowed host.
    return httpx.Client(follow_redirects=False, timeout=get_settings().dhis2_auth_timeout)


def _token_header(token: str) -> dict:
    return {"Authorization": f"ApiToken {token}"}


def fetch_me(client: httpx.Client, url: str, *, auth: tuple | None = None, token: str | None = None) -> dict | None:
    """Return the DHIS2 user for these credentials, or None if DHIS2 rejects them."""
    response = client.get(f"{url}/api/me.json", auth=auth, headers=_token_header(token) if token else None)
    if response.status_code in (401, 403):
        return None
    if response.status_code != 200:
        raise DHIS2Error(f"GET /api/me returned {response.status_code}")
    try:
        data = response.json()
    except ValueError as e:
        raise DHIS2Error("GET /api/me returned invalid JSON") from e
    user = {k: data.get(k) for k in ("id", "email", "username", "displayName")}
    user["is_admin"] = "ALL" in (data.get("authorities") or [])  # DHIS2 superuser
    return user


def create_pat(client: httpx.Client, url: str, auth: tuple, expire_ms: int) -> tuple[str, str]:
    """Create a PAT for the Basic-auth user. Return (key, uid)."""
    response = client.post(
        f"{url}/api/apiToken",
        json={"expire": expire_ms, "attributes": _PAT_ATTRIBUTES},
        auth=auth,
    )
    if response.status_code != 201:
        raise DHIS2Error(f"POST /api/apiToken returned {response.status_code}")
    try:
        body = response.json()["response"]
        key, uid = body["key"], body["uid"]
    except (ValueError, KeyError, TypeError) as e:
        raise DHIS2Error("POST /api/apiToken returned an unexpected body") from e
    if not key.startswith("d2pat_") or not _UID.match(uid):
        raise DHIS2Error("POST /api/apiToken returned an unexpected key or uid")
    return key, uid


def revoke_pat(client: httpx.Client, url: str, uid: str, *, auth: tuple | None = None, token: str | None = None) -> bool:
    """Delete a PAT in DHIS2. Never raises: a failed revocation is logged, the token expires anyway."""
    if not _UID.match(uid):
        logger.warning("Not revoking DHIS2 token: invalid uid")
        return False
    try:
        response = client.delete(
            f"{url}/api/apiToken/{uid}", auth=auth, headers=_token_header(token) if token else None
        )
    except httpx.HTTPError as e:
        logger.warning("Could not revoke DHIS2 token uid=%s: %s", uid, e)
        return False
    if response.status_code != 200:
        logger.warning("DHIS2 refused to revoke token uid=%s: status %s", uid, response.status_code)
        return False
    logger.info("Revoked DHIS2 token uid=%s", uid)
    return True


def user_from_cookies(cookies) -> dict | None:
    """User of the session cookie, valid only while it belongs to the active DHIS2 token."""
    session_id = cookies.get(SESSION_COOKIE)
    session = auth_store.get_session(session_id) if session_id else None
    credential = auth_store.get_credential() if session else None
    if not session or not credential or credential["pat_uid"] != session["pat_uid"]:
        return None
    return session["user"]


async def get_current_user(connection: HTTPConnection) -> dict:
    """Router dependency for HTTP routes and WebSockets alike."""
    is_websocket = connection.scope["type"] == "websocket"
    # CORS does not cover WebSockets: check the origin here (HTTP is checked by check_origin).
    if is_websocket and not is_allowed_origin(connection.headers.get("origin")):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)  # handshake refused
    user = await run_in_threadpool(user_from_cookies, connection.cookies)
    if user is not None:
        return user
    if is_websocket:
        # Accept first: a refused handshake only shows code 1006 to the browser.
        await connection.accept()
        raise WebSocketException(code=WS_NOT_AUTHENTICATED, reason="Not authenticated")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Admin-only routes: DHIS2 superusers (authority ALL). Sessions opened before this check count as non-admin."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrators only")
    return user
