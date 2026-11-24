from fastapi import APIRouter, Query, Depends

from etlhub.api.routers import BLOCKED, CONFIRM_RELAUNCH, WebhookUrl, error_doc
from etlhub.api.routers.etl.ingest_router import add_launch_route
from etlhub.application.use_cases.analytics_service import AnalyticsService
from etlhub.domain.schemas import ETLResponse
from etlhub.core.dependencies import get_analytics_service

router = APIRouter(tags=["Analytics"])

add_launch_route(
    router, "build_analytics", "Build analytics table",
    "Triggers the analytics table construction from ingested data. "
    "Runs etlhub's copy of `etl/scripts/build_analytics.py` asynchronously: waits for DHIS2's end, without limit. ",
    "Analytics build task accepted and queued in background.", "Build analytics task started in background",
)


add_launch_route(
    router, "post_forecast", "Publish forecast results to DHIS2",
    "Publishes the open run's `output/forecast.json`, then `output/alerts.json` if present, to DHIS2, in the "
    "background (a Celery job since 2026-11-24, was synchronous). Its end message says when a CSB run's alert data "
    "was not included (no alerts.json). A success closes the run. ",
    "Task accepted and queued in background.", "Forecast publication started in background",
)


@router.post(
    "/update_key",
    response_model=ETLResponse,
    summary="Update PRIDE-C key in DHIS2 datastore",
    description=(
        "Updates the PRIDE-C datastore key in DHIS2. "
        "Executes `etl/scripts/update_pridec_key.py` synchronously: the request blocks until the script ends "
        "(200 with status success, or 500). `webhook_url` is notified on success only. "
        "Never in test mode (409): test mode is a dry run (DRYRUN = TEST MODE) and pivot_dhis_tools ignores its "
        "dryRun, it would write the key anyway. Production mode only."
    ),
    response_description="PRIDE-C key updated successfully.",
    responses={
        500: error_doc("Internal Server Error - update failed", {"message": "update_key failed: ..."}),
        **BLOCKED,
    },
)
# def, not async: FastAPI runs it in its threadpool, the event loop stays free.
# ponytail: run_etl_job redirects the process-wide stdout/stderr, so prints of other API threads during the run land in
# this job's log (one inline job at a time: the gate). Upgrade: run it through Celery, like post_forecast (2026-11-24).
def api_update_key(
    webhook_url: WebhookUrl = Query(None),
    confirm: bool = CONFIRM_RELAUNCH,
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.update_key(webhook_url, confirm)


add_launch_route(
    router, "calc_orgunit_alerts", "Calculate the org unit alerts of a CSB forecast run",
    "Item {couple}:calc_orgunit_alerts of the open CSB run, between forecast and approve: the number of orgUnits on "
    "alert (forecast mean over 3 months above the mean of the same months over the 3 prior years), from the run's "
    "disease_data.json and forecast.json, written to output/alerts.json, which POST /post_forecast posts with the "
    "forecast. Writes nothing to DHIS2. Focal month: config.json's forecast_start. etlhub's copy of "
    "etl/scripts/calc_orgUnit_alerts.py (application/use_cases/calc_alerts.py). "
    "POST /pipeline/runs/current/skip_alerts still marks the item done without computing anything. ",
    "Task accepted and queued in background.", "Org unit alerts calculation started in background")
