import httpx
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Body, Depends, HTTPException

from etlhub.api.auth.dhis2_auth import get_current_user, get_dhis2_user_info
from etl.scripts.config import get_dhis_url

auth_router = APIRouter()


def _validate_dhis2_url(url: str, settings) -> bool:
    if not url:
        return False
    if not settings.dhis2_allowed_hosts:
        return True
    try:
        host = urlparse(url).netloc
        allowed = [h.strip() for h in settings.dhis2_allowed_hosts.split(",") if h.strip()]
        return host in allowed
    except Exception:
        return False


@auth_router.post("/auth/validate-token")
async def validate_token(
    token: str = Body(..., embed=True),
    dhis2_url: Optional[str] = Body(None),
):
    """Validate a DHIS2 token and return user info."""
    from etlhub.core.config import get_settings

    settings = get_settings()
    url = dhis2_url or get_dhis_url()
    if not url:
        raise HTTPException(
            status_code=500,
            detail="DHIS2 URL not configured",
        )

    if not _validate_dhis2_url(url, settings):
        raise HTTPException(
            status_code=400,
            detail="Invalid or disallowed DHIS2 URL",
        )

    user_info = await get_dhis2_user_info(token=token, dhis2_url=url)

    if not user_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid DHIS2 token",
        )

    return {"user": user_info}


@auth_router.get("/auth/dhis2/login")
async def dhis2_login():
    """Redirect to DHIS2 OAuth authorization endpoint."""
    from etlhub.core.config import get_settings

    settings = get_settings()
    base_url = get_dhis_url()
    if not base_url or not settings.dhis2_client_id:
        raise HTTPException(
            status_code=500,
            detail="DHIS2 OAuth not configured",
        )

    auth_url = (
        f"{base_url.rstrip('/')}/oauth/authorize?"
        f"client_id={settings.dhis2_client_id}&"
        f"response_type=code&"
        f"redirect_uri={settings.dhis2_redirect_uri}"
    )
    return {"auth_url": auth_url}


@auth_router.post("/auth/dhis2/callback")
async def dhis2_callback(code: str):
    """Exchange authorization code for access token."""
    from etlhub.core.config import get_settings

    settings = get_settings()
    base_url = get_dhis_url()
    if not base_url or not settings.dhis2_client_id or not settings.dhis2_client_secret:
        raise HTTPException(
            status_code=500,
            detail="DHIS2 OAuth not configured",
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.dhis2_client_id,
                    "client_secret": settings.dhis2_client_secret,
                    "redirect_uri": settings.dhis2_redirect_uri,
                },
                timeout=settings.dhis2_auth_timeout,
            )
            if response.status_code == 200:
                token_data = response.json()
                user_info = await get_dhis2_user_info(token=token_data["access_token"])
                return {"access_token": token_data["access_token"], "user": user_info}
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to obtain access token from DHIS2",
                )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"DHIS2 OAuth error: {str(e)}",
        )


@auth_router.get("/auth/me", dependencies=[Depends(get_current_user)])
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return user