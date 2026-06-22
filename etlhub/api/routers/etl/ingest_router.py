import uuid
from fastapi import APIRouter, Query

from etlhub.infrastructure.tasks import (
    task_import_gee,
    task_import_pivot_com,
    task_import_pivot_csb,
    task_fetch_climate,
    task_fetch_disease,
    task_fetch_geojson,
)
from etlhub.domain.schemas import ETLResponse

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
async def api_import_gee(webhook_url: str | None = Query(None)):
    job_id = f"import_gee_{uuid.uuid4().hex[:8]}"
    task_import_gee.delay(job_id, webhook_url=webhook_url)
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
async def api_import_pivot_com(webhook_url: str | None = Query(None)):
    job_id = f"import_pivot_com_{uuid.uuid4().hex[:8]}"
    task_import_pivot_com.delay(job_id, webhook_url=webhook_url)
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
async def api_import_pivot_csb(webhook_url: str | None = Query(None)):
    job_id = f"import_pivot_csb_{uuid.uuid4().hex[:8]}"
    task_import_pivot_csb.delay(job_id, webhook_url=webhook_url)
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
async def api_fetch_climate(webhook_url: str | None = Query(None)):
    job_id = f"fetch_climate_{uuid.uuid4().hex[:8]}"
    task_fetch_climate.delay(job_id, webhook_url=webhook_url)
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
async def api_fetch_disease(webhook_url: str | None = Query(None)):
    job_id = f"fetch_disease_{uuid.uuid4().hex[:8]}"
    task_fetch_disease.delay(job_id, webhook_url=webhook_url)
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
async def api_fetch_geojson(webhook_url: str | None = Query(None)):
    job_id = f"fetch_geojson_{uuid.uuid4().hex[:8]}"
    task_fetch_geojson.delay(job_id, webhook_url=webhook_url)
    return ETLResponse(
        status="accepted",
        message="Fetch geojson task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )