import logging
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from etlhub.api.routers import error_doc
from etlhub.application.use_cases import fetch_pivot
from etlhub.application.use_cases.ingestion_service import available_gee_variables
from etlhub.core.dependencies import get_auth_store, get_config_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["Configuration"])

# DHIS_URL and DHIS_TOKEN are not here: they come from the DHIS2 login only (auth_store).
# No DRYRUN: the mode decides it (DRYRUN = TEST MODE, PUT /pipeline/mode).
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

class ConfigUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    parent_ou: str | None = Field(None)
    ou_level: int | None = Field(None, ge=1, le=10)
    disease_code: str | None = Field(None)
    log_level: LogLevel | None = Field(None)
    pivot_url: str | None = Field(None, pattern=r"^https?://\S+$", description="The Pivot DHIS2 the imports read from")

class ConfigResponse(BaseModel):
    # Read-only, from the DHIS2 login. The token itself is never returned.
    dhis_url: str | None = None
    has_dhis_token: bool = False
    dhis_token_expires_at: int | None = None
    parent_ou: str | None = None
    ou_level: int | None = None
    disease_code: str | None = None
    log_level: str | None = None
    pivot_url: str | None = None
    # PIVOT_TOKEN is in etlhub's environment (.env), never in Redis nor here: whether it is set only.
    has_pivot_token: bool = False
    # Read only: every GEE variable of pridec_gee. Each pass chooses its own when it starts (POST /pipeline/passes).
    gee_variables: list[str] = []

@router.get(
    "/",
    response_model=ConfigResponse,
    summary="Current dynamic configuration",
    description=(
        "PARENT_OU, OU_LEVEL, DISEASE_CODE, LOG_LEVEL and PIVOT_URL from Redis, plus the DHIS2 URL and token expiry of "
        "the last login. No token is ever returned (has_dhis_token, has_pivot_token only: PIVOT_TOKEN stays in etlhub's "
        "environment). gee_variables: every GEE variable of pridec_gee, "
        "read only (a pass chooses its own when it starts)."
    ),
)
async def get_config():
    data = get_config_store().get_all()
    credential = get_auth_store().get_credential() or {}
    return ConfigResponse(
        dhis_url=credential.get("url"),
        has_dhis_token=bool(credential.get("token")),
        dhis_token_expires_at=credential.get("expires_at"),
        parent_ou=data.get("PARENT_OU"),
        ou_level=int(data["OU_LEVEL"]) if data.get("OU_LEVEL") else None,
        disease_code=data.get("DISEASE_CODE"),
        log_level=data.get("LOG_LEVEL"),
        pivot_url=data.get("PIVOT_URL"),
        has_pivot_token=fetch_pivot.has_pivot_token(),
        gee_variables=available_gee_variables(),
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
    if updates and not get_config_store().set_all(updates):
        raise HTTPException(status_code=502, detail="Failed to write config to Redis")
    return await get_config()

@router.put(
    "/reload",
    response_model=ConfigResponse,
    summary="Reload the dynamic configuration from .env",
    responses={502: error_doc("Redis write failed", {"detail": "Failed to write config to Redis"})},
)
async def reload_config():
    """Rereads the editable keys (config_store.EDITABLE_KEYS) from etlhub's .env and writes them to Redis,
    overwriting the current values, as the API does at each start. A key missing from .env is removed from Redis.
    Use it after editing .env by hand."""
    if not get_config_store().load_env():
        raise HTTPException(status_code=502, detail="Failed to write config to Redis")
    return await get_config()
