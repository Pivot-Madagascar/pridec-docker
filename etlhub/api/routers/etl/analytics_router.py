from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse

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


@router.post(
    "/post_forecast",
    response_model=ETLResponse,
    summary="Publish forecast results to DHIS2",
    description=(
        "Publishes `output/forecast.json`, then `output/alerts.json` if present, to DHIS2. "
        "Runs synchronously: the request blocks until both are posted "
        "(200 with status success, or 500). `webhook_url` is notified on success only."
    ),
    response_description="Forecast published successfully to DHIS2.",
    responses={
        500: error_doc("Internal Server Error - publish failed", {"message": "post_forecast failed: ..."}),
        **BLOCKED,
    },
)
# def, not async: FastAPI runs it in its threadpool, the event loop stays free.
# ponytail: run_etl_job redirects the process-wide stdout/stderr, so prints of other API threads during the run land in
# this job's log (one inline job at a time: the gate). Upgrade: run both through Celery (etlhub-practices, migration m2).
def api_post_forecast(
    webhook_url: WebhookUrl = Query(None),
    confirm: bool = CONFIRM_RELAUNCH,
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.post_forecast(webhook_url, confirm)


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
def api_update_key(  # def, not async: see api_post_forecast
    webhook_url: WebhookUrl = Query(None),
    confirm: bool = CONFIRM_RELAUNCH,
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.update_key(webhook_url, confirm)


@router.post(
    "/calc_orgunit_alerts",
    status_code=501,
    summary="Calculate the org unit alerts of a CSB forecast run (not implemented)",
    description=(
        "Item {couple}:calc_orgunit_alerts of the CSB runs, between forecast and approve. "
        "No script implements it yet (no etl/scripts module, nothing in pivot_dhis_tools): "
        "CSB runs, and so the cycle, cannot complete until it exists. "
        "POST /pipeline/runs/current/skip_alerts marks the item done meanwhile."
    ),
    responses={501: error_doc("Always: no script exists yet",
                              {"message": "calc_orgunit_alerts is not implemented: no script exists for it yet"})},
)
async def api_calc_orgunit_alerts():
    return JSONResponse(status_code=501, content={
        "message": "calc_orgunit_alerts is not implemented: no script exists for it yet",
    })
