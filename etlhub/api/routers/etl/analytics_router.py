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
    "Executes `etl/scripts/build_analytics.py` asynchronously. ",
    "Analytics build task accepted and queued in background.", "Build analytics task started in background",
)


@router.post(
    "/post_forecast",
    response_model=ETLResponse,
    summary="Publish forecast results to DHIS2",
    description=(
        "Publishes the latest forecast results to DHIS2. "
        "Executes `etl/scripts/post_forecast.py` synchronously: the request blocks until the script ends "
        "(200 with status success, or 500). `webhook_url` is notified on success only."
    ),
    response_description="Forecast published successfully to DHIS2.",
    responses={
        500: {
            "description": "Internal Server Error - publish failed",
            "content": {
                "application/json": {
                    "example": {"message": "post_forecast failed: ..."}
                }
            },
        },
        **BLOCKED,
    },
)
async def api_post_forecast(
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
        "(200 with status success, or 500). `webhook_url` is notified on success only."
    ),
    response_description="PRIDE-C key updated successfully.",
    responses={
        500: {
            "description": "Internal Server Error - update failed",
            "content": {
                "application/json": {
                    "example": {"message": "update_key failed: ..."}
                }
            },
        },
        **BLOCKED,
    },
)
async def api_update_key(
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
