from fastapi import APIRouter, Query, Depends

from etlhub.api.routers import BLOCKED, CONFIRM_OVERWRITE, WebhookUrl
from etlhub.application.use_cases.ingestion_service import IngestionService
from etlhub.domain.schemas import ETLResponse, InputPath
from etlhub.core.dependencies import get_ingestion_service

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
    responses=BLOCKED,
)
async def api_validate_inputs(
    config_path: InputPath | None = Query(None, description="Path to config.json, under input/"),
    external_data_path: InputPath | None = Query(None, description="Path to external_data.csv, under input/"),
    disease_data_path: InputPath | None = Query(None, description="Path to disease_data.json, under input/"),
    climate_data_path: InputPath | None = Query(None, description="Path to climate_data.json, under input/"),
    orgunit_poly_path: InputPath | None = Query(None, description="Path to orgUnit_poly.geojson, under input/"),
    input_dir: InputPath | None = Query(None, description="Subdirectory of input/, e.g. input/run1 (default: input)"),
    webhook_url: WebhookUrl = Query(None, description="Optional webhook callback URL"),
    confirm: bool = CONFIRM_OVERWRITE,
    service: IngestionService = Depends(get_ingestion_service),
):
    job_id = service.launch(
        "validate_inputs",
        webhook_url=webhook_url,
        confirm=confirm,
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