import uuid
from fastapi import APIRouter, HTTPException, Depends, Query

from etlhub.application.use_cases.etl_use_cases import (
    ETLException,
    run_post_forecast,
    run_update_key,
)
from etlhub.infrastructure.tasks import (
    task_build_analytics,
    task_calc_csb_alerts,
    _send_webhook,
)
from etlhub.infrastructure.job_store import JobStore
from etlhub.domain.schemas import ETLResponse

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
async def api_build_analytics(webhook_url: str | None = Query(None)):
    job_id = f"build_analytics_{uuid.uuid4().hex[:8]}"
    task_build_analytics.delay(job_id, webhook_url=webhook_url)
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
async def api_post_forecast(webhook_url: str | None = Query(None)):
    job_id = f"post_forecast_{uuid.uuid4().hex[:8]}"
    job_store = JobStore()
    try:
        run_post_forecast(job_store=job_store, job_id=job_id)
        result = ETLResponse(status="success", message="Forecast posted successfully", job_id=job_id, webhook_url=webhook_url)
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))
    if webhook_url:
        _send_webhook(webhook_url, job_id=job_id, status="success", message="Forecast posted successfully", logs_url=f"/api/tracking/etl-logs/{job_id}")
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
async def api_calc_csb_alerts(webhook_url: str | None = Query(None)):
    job_id = f"calc_csb_alerts_{uuid.uuid4().hex[:8]}"
    task_calc_csb_alerts.delay(job_id, webhook_url=webhook_url)
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
async def api_update_key(webhook_url: str | None = Query(None)):
    job_id = f"update_key_{uuid.uuid4().hex[:8]}"
    job_store = JobStore()
    try:
        run_update_key(job_store=job_store, job_id=job_id)
        result = ETLResponse(status="success", message="Key updated successfully", job_id=job_id, webhook_url=webhook_url)
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))
    if webhook_url:
        _send_webhook(webhook_url, job_id=job_id, status="success", message="Key updated successfully", logs_url=f"/api/tracking/etl-logs/{job_id}")
    return result