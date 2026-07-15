import logging
import time
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from etlhub.core.config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

_token_cache: dict = {}
_cache_ttl_seconds = 120


def _get_cached_user_info(token: str) -> Optional[dict]:
    entry = _token_cache.get(token)
    if entry and time.time() - entry["timestamp"] < _cache_ttl_seconds:
        return entry["user_info"]
    return None


def _set_cached_user_info(token: str, user_info: Optional[dict]) -> None:
    if user_info:
        _token_cache[token] = {"user_info": user_info, "timestamp": time.time()}


def _clean_cache() -> None:
    now = time.time()
    expired = [t for t, e in _token_cache.items() if now - e["timestamp"] >= _cache_ttl_seconds]
    for t in expired:
        del _token_cache[t]


async def get_dhis2_user_info(
    token: Optional[str] = None,
    user: Optional[str] = None,
    pwd: Optional[str] = None,
    dhis2_url: Optional[str] = None,
) -> Optional[dict]:
    settings = get_settings()
    base_url = (dhis2_url or settings.dhis2_url).rstrip('/')
    if not base_url:
        return None

    if not token and not (user and pwd):
        raise ValueError("Authentication required: provide either a token or both user and pwd")

    if token:
        cached = _get_cached_user_info(token)
        if cached:
            return cached

    headers = {"Authorization": f"ApiToken {token}"} if token else {}
    auth = None if token else httpx.BasicAuth(user, pwd)

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                f"{base_url}/api/me.json",
                headers=headers,
                auth=auth,
                timeout=settings.dhis2_auth_timeout,
            )
            if response.status_code == 200:
                try:
                    data = response.json()
                except (ValueError, Exception):
                    logger.error("DHIS2 returned invalid JSON response")
                    return None
                user_info = {
                    "id": data.get("id"),
                    "email": data.get("email"),
                    "username": data.get("username"),
                    "displayName": data.get("displayName"),
                }
                if token:
                    _set_cached_user_info(token, user_info)
                    _clean_cache()
                return user_info
            if response.status_code in (401, 403):
                logger.warning(
                    "DHIS2 authentication failed for user=%s with status=%s",
                    user or "unknown",
                    response.status_code,
                )
                return None
            response_text = response.text[:200] if response.text else "no content"
            logger.error(
                "DHIS2 returned unexpected status %s: %s",
                response.status_code,
                response_text,
            )
            return None
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(
            "DHIS2 unreachable for user=%s: %s",
            user or "unknown",
            str(e)[:100],
        )
        return None
    except Exception:
        logger.exception("Unexpected error validating DHIS2 credentials")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_info = await get_dhis2_user_info(token=credentials.credentials)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired DHIS2 token",
        )

    logger.info("User authenticated successfully: id=%s", user_info.get("id"))
    return user_info