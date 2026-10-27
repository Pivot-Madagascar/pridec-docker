from fastapi import APIRouter, Query, Depends

from etlhub.api.routers import BLOCKED, CONFIRM_OVERWRITE, CONFIRM_RELAUNCH, WebhookUrl, error_doc
from etlhub.application.use_cases.availability_service import AvailabilityService
from etlhub.application.use_cases.ingestion_service import IngestionService
from etlhub.domain.schemas import ETLResponse, ImportAvailabilityReport
from etlhub.core.dependencies import get_availability_service, get_ingestion_service

router = APIRouter(tags=["Ingest"])


def add_launch_route(router: APIRouter, task_type: str, summary: str, description: str, response_description: str,
                     message: str, confirm_query=CONFIRM_RELAUNCH) -> None:
    """POST /{task_type}: queues the Celery job, 202 with its job_id."""
    async def endpoint(
        webhook_url: WebhookUrl = Query(None),
        confirm: bool = confirm_query,
        service: IngestionService = Depends(get_ingestion_service),
    ):
        job_id = service.launch(task_type, webhook_url, confirm)
        return ETLResponse(status="accepted", message=message, job_id=job_id, webhook_url=webhook_url)

    router.post(
        f"/{task_type}",
        response_model=ETLResponse,
        status_code=202,
        summary=summary,
        description=description + "Pass `webhook_url` to be notified when the job completes.",
        response_description=response_description,
        responses=BLOCKED,
        name=f"api_{task_type}",
    )(endpoint)


for _args in [
    ("import_gee", "Import GEE data into DHIS2",
     "Launches the GEE import process in the background. Executes `etl/scripts/import_gee.py` asynchronously. ",
     "Task accepted and queued in background.", "Import GEE task started in background"),
    ("import_pivot_com", "Import Pivot COM data into DHIS2",
     "Launches the Pivot COM historical data import in the background. "
     "Executes `etl/scripts/import_pivot_COM.py` asynchronously. ",
     "Task accepted and queued in background.", "Import Pivot COM task started in background"),
    ("import_pivot_csb", "Import Pivot CSB data into DHIS2",
     "Launches the Pivot CSB historical data import in the background. "
     "Executes `etl/scripts/import_pivot_CSB.py` asynchronously. ",
     "Task accepted and queued in background.", "Import Pivot CSB task started in background"),
    ("fetch_climate", "Fetch climate data from external source",
     "Launches the climate data fetch in the background. Executes `etl/scripts/fetch_pridec_climate.py` asynchronously. ",
     "Climate data fetch accepted and queued in background.", "Fetch climate task started in background",
     CONFIRM_OVERWRITE),
    ("fetch_disease", "Fetch disease data from external source",
     "Launches the disease data fetch in the background. Executes `etl/scripts/fetch_pridec_disease.py` asynchronously. ",
     "Disease data fetch accepted and queued in background.", "Fetch disease task started in background",
     CONFIRM_OVERWRITE),
    ("fetch_geojson", "Fetch GeoJSON data from external source",
     "Launches the GeoJSON boundary data fetch in the background. "
     "Executes `etl/scripts/fetch_pridec_geojson.py` asynchronously. ",
     "GeoJSON data fetch accepted and queued in background.", "Fetch geojson task started in background",
     CONFIRM_OVERWRITE),
]:
    add_launch_route(router, *_args)


# Sync def: FastAPI runs it in its threadpool, the DHIS2 requests (a few seconds) never block the event loop.
@router.get(
    "/import_availability",
    response_model=ImportAvailabilityReport,
    summary="Is the data of import_gee, import_pivot_com and import_pivot_csb already in DHIS2?",
    description=(
        "Runs `etl/scripts/check_import_availability.py` synchronously, read only, with the session's DHIS2 token: "
        "per dataElement and period, the orgUnits with a stored value (`raw`, /api/dataValueSets) and with a value "
        "in analytics (`analytics`), plus DHIS2's last analytics build. Same periods and orgUnits as the imports. "
        "Shared: a section (one import) checked in the cycle (any pass, any user) is reused (`reused: true`) while "
        "its parameters are the same, it is at most 30 days old and that import was not launched since. "
        "`refresh=true` checks every section again. Journaled (`availability_checked`, or `availability_reused` when "
        "DHIS2 was not asked, step data_import) in the pass the Dashboard shows, so tracked too. "
        "A DHIS2 error on one dataElement only fills its `error`."
    ),
    responses={500: error_doc("The check could not run (missing PARENT_OU, no DHIS2 session)",
                              {"message": "Import availability check failed: ..."})},
)
def api_import_availability(
    refresh: bool = Query(False, description="Check every section in DHIS2 again, even those still valid"),
    service: AvailabilityService = Depends(get_availability_service),
):
    return service.check(refresh)
