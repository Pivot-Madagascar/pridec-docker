import logging
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from dotenv import dotenv_values

from etlhub.api.auth.dhis2_auth import get_current_user
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

@router.get("/", response_model=ConfigResponse, dependencies=[Depends(get_current_user)])
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

@router.put("/", response_model=ConfigResponse, dependencies=[Depends(get_current_user)])
async def update_config(config: ConfigUpdate):
    updates = {k.upper(): v for k, v in config.model_dump(exclude_none=True).items()}
    if updates and not ConfigStore().set_all(updates):
        raise HTTPException(status_code=502, detail="Failed to write config to Redis")
    return await get_config()

@router.put("/reload", response_model=ConfigResponse, dependencies=[Depends(get_current_user)])
async def reload_config():
    """
    Relit les variables éditables depuis le fichier .env (racine du projet)
    et les réécrit dans Redis, écrasant les valeurs actuelles de ConfigStore.
    Utile pour resynchroniser après une modification manuelle du .env.
    """
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