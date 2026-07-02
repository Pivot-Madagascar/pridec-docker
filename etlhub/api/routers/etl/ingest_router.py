from fastapi import APIRouter, Query, Depends

from etlhub.application.use_cases.ingestion_service import IngestionService
from etlhub.domain.schemas import ETLResponse
from etlhub.core.dependencies import get_ingestion_service

router = APIRouter(tags=["Ingest"])


@router.post(
    "/import_gee",
    response_model=ETLResponse,
    status_code=202,
    summary="Import GEE data into DHIS2",
    description=(
        "Launches the GEE import process in the background. "
        "Executes `etl/scripts/import_gee.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="Task accepted and queued in background.",
)
async def api_import_gee(
    webhook_url: str | None = Query(None),
    service: IngestionService = Depends(get_ingestion_service),
):
    job_id = service.import_gee(webhook_url)
    return ETLResponse(
        status="accepted",
        message="Import GEE task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )


@router.post(
    "/import_pivot_com",
    response_model=ETLResponse,
    status_code=202,
    summary="Import Pivot COM data into DHIS2",
    description=(
        "Launches the Pivot COM historical data import in the background. "
        "Executes `etl/scripts/import_pivot_COM.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="Task accepted and queued in background.",
)
async def api_import_pivot_com(
    webhook_url: str | None = Query(None),
    service: IngestionService = Depends(get_ingestion_service),
):
    job_id = service.import_pivot_com(webhook_url)
    return ETLResponse(
        status="accepted",
        message="Import Pivot COM task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )


@router.post(
    "/import_pivot_csb",
    response_model=ETLResponse,
    status_code=202,
    summary="Import Pivot CSB data into DHIS2",
    description=(
        "Launches the Pivot CSB historical data import in the background. "
        "Executes `etl/scripts/import_pivot_CSB.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="Task accepted and queued in background.",
)
async def api_import_pivot_csb(
    webhook_url: str | None = Query(None),
    service: IngestionService = Depends(get_ingestion_service),
):
    job_id = service.import_pivot_csb(webhook_url)
    return ETLResponse(
        status="accepted",
        message="Import Pivot CSB task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )


@router.post(
    "/fetch_climate",
    response_model=ETLResponse,
    status_code=202,
    summary="Fetch climate data from external source",
    description=(
        "Launches the climate data fetch in the background. "
        "Executes `etl/scripts/fetch_pridec_climate.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="Climate data fetch accepted and queued in background.",
)
async def api_fetch_climate(
    webhook_url: str | None = Query(None),
    service: IngestionService = Depends(get_ingestion_service),
):
    job_id = service.fetch_climate(webhook_url)
    return ETLResponse(
        status="accepted",
        message="Fetch climate task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )


@router.post(
    "/fetch_disease",
    response_model=ETLResponse,
    status_code=202,
    summary="Fetch disease data from external source",
    description=(
        "Launches the disease data fetch in the background. "
        "Executes `etl/scripts/fetch_pridec_disease.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="Disease data fetch accepted and queued in background.",
)
async def api_fetch_disease(
    webhook_url: str | None = Query(None),
    service: IngestionService = Depends(get_ingestion_service),
):
    job_id = service.fetch_disease(webhook_url)
    return ETLResponse(
        status="accepted",
        message="Fetch disease task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )


@router.post(
    "/fetch_geojson",
    response_model=ETLResponse,
    status_code=202,
    summary="Fetch GeoJSON data from external source",
    description=(
        "Launches the GeoJSON boundary data fetch in the background. "
        "Executes `etl/scripts/fetch_pridec_geojson.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="GeoJSON data fetch accepted and queued in background.",
)
async def api_fetch_geojson(
    webhook_url: str | None = Query(None),
    service: IngestionService = Depends(get_ingestion_service),
):
    job_id = service.fetch_geojson(webhook_url)
    return ETLResponse(
        status="accepted",
        message="Fetch geojson task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )