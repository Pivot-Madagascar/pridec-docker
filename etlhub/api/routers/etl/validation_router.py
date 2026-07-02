import uuid
from fastapi import APIRouter, Query, Depends

from etlhub.application.use_cases.validation_service import ValidationService
from etlhub.domain.schemas import ETLResponse
from etlhub.core.dependencies import get_validation_service

router = APIRouter(tags=["Validation"])


@router.post(
    "/validate_inputs",
    response_model=ETLResponse,
    status_code=202,
    summary="Validate PRIDE-C forecast input data",
    description=(
        "Launches input validation in the background. "
        "Executes `etl/scripts/validate_inputs.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes. "
        "Connect to `/api/tracking/etl-logs/{job_id}` for live progress."
    ),
    response_description="Validation task accepted and queued in background.",
)
async def api_validate_inputs(
    config_path: str | None = Query(None, description="Path to config.json"),
    external_data_path: str | None = Query(None, description="Path to external_data.csv"),
    disease_data_path: str | None = Query(None, description="Path to disease_data.json"),
    climate_data_path: str | None = Query(None, description="Path to climate_data.json"),
    orgunit_poly_path: str | None = Query(None, description="Path to orgUnit_poly.geojson"),
    input_dir: str | None = Query(None, description="Base input directory (default: input/)"),
    webhook_url: str | None = Query(None, description="Optional webhook callback URL"),
    service: ValidationService = Depends(get_validation_service),
):
    job_id = service.validate_inputs(
        webhook_url=webhook_url,
        config_path=config_path,
        external_data_path=external_data_path,
        disease_data_path=disease_data_path,
        climate_data_path=climate_data_path,
        orgunit_poly_path=orgunit_poly_path,
        input_dir=input_dir,
    )
    return ETLResponse(
        status="accepted",
        message="Validate inputs task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )