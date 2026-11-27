"""Login rules (allowed DHIS2 hosts, cookies, lifetimes) and the session dependency.

Login exchanges a DHIS2 username/password for a personal access token (PAT), through the DHIS2Accounts port. The PAT
never leaves the server: the browser only gets an HttpOnly session cookie.
"""
from urllib.parse import urlparse

from fastapi import HTTPException, WebSocketException, status
from starlette.concurrency import run_in_threadpool
from starlette.requests import HTTPConnection

from etlhub.api.middleware import is_allowed_origin
from etlhub.core.config import get_settings, split_csv
from etlhub.core.job_context import pipeline_test_mode
from etlhub.core.request_context import request_context
from etlhub.core.dependencies import get_auth_store

SESSION_COOKIE = "etlhub_session"
# A random id per browser (never the token), kept 30 days: a new login from the browser that created the account's
# token reuses it; a login from another browser replaces it.
DEVICE_COOKIE = "etlhub_device"
# WebSocket close code when the session is missing or no longer valid. etlui sends the
# user back to /login on it (useWebSocketLogger.ts).
WS_NOT_AUTHENTICATED = 4401
# The browser session (and its cookie) ends after 24 h; each account's DHIS2 token lives 30 days (router.login).
SESSION_LIFETIME_SECONDS = 24 * 3600
TOKEN_LIFETIME_SECONDS = 30 * 24 * 3600

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def allowed_hosts() -> list[str]:
    """DHIS2_ALLOWED_HOSTS as lowercase host[:port], in order."""
    return [h.lower() for h in split_csv(get_settings().dhis2_allowed_hosts)]


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
    if parsed.netloc.lower() not in allowed_hosts():
        return None
    return url.strip().rstrip("/")


def session_from_cookies(cookies) -> dict | None:
    """Session of the cookie ({user, pat_uid, test_mode}), valid only while it belongs to its account's DHIS2 token."""
    session_id = cookies.get(SESSION_COOKIE)
    session = get_auth_store().get_session(session_id) if session_id else None
    credential = get_auth_store().get_credential(session["user"]["username"]) if session else None
    if not session or not credential or credential["pat_uid"] != session["pat_uid"]:
        return None
    return session


async def get_current_user(connection: HTTPConnection) -> dict:
    """Router dependency for HTTP routes and WebSockets alike."""
    is_websocket = connection.scope["type"] == "websocket"
    # CORS does not cover WebSockets: check the origin here (HTTP is checked by check_origin).
    if is_websocket and not is_allowed_origin(connection.headers.get("origin")):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)  # handshake refused
    session = await run_in_threadpool(session_from_cookies, connection.cookies)
    if session is not None:
        user = session["user"]
        # The user's mode serves this request (and the jobs it launches); a session from before it had none: test.
        test_mode = session.get("test_mode", True)
        pipeline_test_mode.set(test_mode)
        if (context := request_context.get()) is not None:
            context["actor"] = user.get("username")  # the pipeline journal records who acted
            context["mode"] = "test" if test_mode else "production"  # the request log's mode (middleware)
        return user
    if is_websocket:
        # Accept first: a refused handshake only shows code 1006 to the browser.
        await connection.accept()
        raise WebSocketException(code=WS_NOT_AUTHENTICATED, reason="Not authenticated")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
