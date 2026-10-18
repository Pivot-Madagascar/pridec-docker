import logging
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from dotenv import dotenv_values

from etlhub.api.routers import error_doc
from etlhub.infrastructure.config_store import ConfigStore
from etlhub.infrastructure.auth_store import get_credential

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["Configuration"])

# DHIS_URL and DHIS_TOKEN are not here: they come from the DHIS2 login only (auth_store).
_RELOADABLE_KEYS = ["PARENT_OU", "OU_LEVEL", "DISEASE_CODE"]

class ConfigUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    parent_ou: str | None = Field(None)
    ou_level: int | None = Field(None, ge=1, le=10)
    disease_code: str | None = Field(None)

class ConfigResponse(BaseModel):
    # Read-only, from the DHIS2 login. The token itself is never returned.
    dhis_url: str | None = None
    has_dhis_token: bool = False
    dhis_token_expires_at: int | None = None
    parent_ou: str | None = None
    ou_level: int | None = None
    disease_code: str | None = None

@router.get(
    "/",
    response_model=ConfigResponse,
    summary="Current dynamic configuration",
    description=(
        "PARENT_OU, OU_LEVEL and DISEASE_CODE from Redis, plus the DHIS2 URL and token expiry of the last login. "
        "The token itself is never returned (has_dhis_token only)."
    ),
)
async def get_config():
    data = ConfigStore().get_all()
    credential = get_credential() or {}
    return ConfigResponse(
        dhis_url=credential.get("url"),
        has_dhis_token=bool(credential.get("token")),
        dhis_token_expires_at=credential.get("expires_at"),
        parent_ou=data.get("PARENT_OU"),
        ou_level=int(data["OU_LEVEL"]) if data.get("OU_LEVEL") else None,
        disease_code=data.get("DISEASE_CODE"),
    )

@router.put(
    "/",
    response_model=ConfigResponse,
    summary="Update the dynamic configuration",
    description="Writes the fields that are set (null fields are left as they are) and returns the new configuration.",
    responses={502: error_doc("Redis write failed", {"detail": "Failed to write config to Redis"})},
)
async def update_config(config: ConfigUpdate):
    updates = {k.upper(): v for k, v in config.model_dump(exclude_none=True).items()}
    if updates and not ConfigStore().set_all(updates):
        raise HTTPException(status_code=502, detail="Failed to write config to Redis")
    return await get_config()

@router.put(
    "/reload",
    response_model=ConfigResponse,
    summary="Reload the dynamic configuration from .env",
    responses={502: error_doc("Redis write failed", {"detail": "Failed to write config to Redis"})},
)
async def reload_config():
    """Rereads PARENT_OU, OU_LEVEL and DISEASE_CODE from the root .env and writes them to Redis,
    overwriting the current values. A key missing from .env is removed from Redis.
    Use it after editing .env by hand."""
    _PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    env_values = dotenv_values(env_path)

    updates = {k: v for k, v in env_values.items() if k in _RELOADABLE_KEYS and v is not None}
    
    # Supprimer les clés qui sont dans _RELOADABLE_KEYS mais pas dans .env
    current_config = ConfigStore().get_all()
    keys_to_remove = [k for k in _RELOADABLE_KEYS if k not in env_values or env_values.get(k) is None]
    
    if keys_to_remove and not ConfigStore().delete_keys(keys_to_remove):
        raise HTTPException(status_code=502, detail="Failed to sync removed config keys in Redis")
    if updates and not ConfigStore().set_all(updates):
        raise HTTPException(status_code=502, detail="Failed to write reloaded config to Redis")

    return await get_config()