from fastapi import APIRouter, HTTPException, Query, Depends

from etlhub.application.use_cases.analytics_service import AnalyticsService
from etlhub.domain.schemas import ETLResponse
from etlhub.domain.exceptions import ETLException
from etlhub.core.dependencies import get_analytics_service

router = APIRouter(tags=["Analytics"])


@router.post(
    "/build_analytics",
    response_model=ETLResponse,
    status_code=202,
    summary="Build analytics table",
    description=(
        "Triggers the analytics table construction from ingested data. "
        "Executes `etl/scripts/build_analytics.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="Analytics build task accepted and queued in background.",
)
async def api_build_analytics(
    webhook_url: str | None = Query(None),
    service: AnalyticsService = Depends(get_analytics_service),
):
    job_id = service.build_analytics(webhook_url)
    return ETLResponse(
        status="accepted",
        message="Build analytics task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )


@router.post(
    "/post_forecast",
    response_model=ETLResponse,
    summary="Publish forecast results to DHIS2",
    description=(
        "Publishes the latest forecast results to DHIS2. "
        "Executes `etl/scripts/post_forecast.py` synchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="Forecast published successfully to DHIS2.",
    responses={
        500: {
            "description": "Internal Server Error - publish failed",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ETLResponse"},
                    "example": {"status": "error", "message": "post_forecast failed: ..."},
                }
            },
        }
    },
)
async def api_post_forecast(
    webhook_url: str | None = Query(None),
    service: AnalyticsService = Depends(get_analytics_service),
):
    try:
        result = service.post_forecast(webhook_url)
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


@router.post(
    "/calc_csb_alerts",
    response_model=ETLResponse,
    status_code=202,
    summary="Calculate and publish CSB alerts",
    description=(
        "Executes `etl/scripts/calc_CSB_alerts.py` "
        "asynchronously. Returns a `job_id` for progress tracking. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="CSB alert calculation task accepted and queued in background.",
)
async def api_calc_csb_alerts(
    webhook_url: str | None = Query(None),
    service: AnalyticsService = Depends(get_analytics_service),
):
    job_id = service.calc_csb_alerts(webhook_url)
    return ETLResponse(
        status="accepted",
        message="Calculate CSB alerts task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )


@router.post(
    "/update_key",
    response_model=ETLResponse,
    summary="Update PRIDE-C key in DHIS2 datastore",
    description=(
        "Updates the PRIDE-C datastore key in DHIS2. "
        "Executes `etl/scripts/update_pridec_key.py` synchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="PRIDE-C key updated successfully.",
    responses={
        500: {
            "description": "Internal Server Error - update failed",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ETLResponse"},
                    "example": {"status": "error", "message": "update_pridec_key failed: ..."},
                }
            },
        }
    },
)
async def api_update_key(
    webhook_url: str | None = Query(None),
    service: AnalyticsService = Depends(get_analytics_service),
):
    try:
        result = service.update_key(webhook_url)
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result