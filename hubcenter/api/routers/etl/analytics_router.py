from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends

from hubcenter.application.use_cases.etl_use_cases import (
    ETLException,
    run_build_analytics,
    run_post_forecast,
    run_calc_csb_alerts,
    run_update_key,
)
from hubcenter.domain.schemas import ETLResponse
from hubcenter.api.dependencies import get_job_store

router = APIRouter(tags=["Analytics"])


@router.post(
    "/build_analytics",
    response_model=ETLResponse,
    status_code=202,
    summary="Build analytics table",
    description=(
        "Triggers the analytics table construction from ingested data. "
        "Executes `etl/scripts/build_analytics.py` asynchronously. "
    ),
    response_description="Analytics build task accepted and queued in background.",
)
async def api_build_analytics(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_build_analytics)
    return ETLResponse(status="accepted", message="Build analytics task started in background")


@router.post(
    "/post_forecast",
    response_model=ETLResponse,
    summary="Publish forecast results to DHIS2",
    description=(
        "Publishes the latest forecast results to DHIS2. "
        "Executes `etl/scripts/post_forecast.py` synchronously. "
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
async def api_post_forecast():
    try:
        run_post_forecast()
        return ETLResponse(status="success", message="Forecast posted successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/calc_csb_alerts",
    response_model=ETLResponse,
    status_code=202,
    summary="Calculate and publish CSB alerts",
    description=(
        "Executes `etl/scripts/calc_CSB_alerts.py` "
        "asynchronously. Returns a `job_id` for progress tracking."
    ),
    response_description="CSB alert calculation task accepted and queued in background.",
)
async def api_calc_csb_alerts(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_calc_csb_alerts)
    return ETLResponse(status="accepted", message="Calculate CSB alerts task started in background")


@router.post(
    "/update_key",
    response_model=ETLResponse,
    summary="Update PRIDE-C key in DHIS2 datastore",
    description=(
        "Updates the PRIDE-C datastore key in DHIS2. "
        "Executes `etl/scripts/update_pridec_key.py` synchronously. "
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
async def api_update_key():
    try:
        run_update_key()
        return ETLResponse(status="success", message="Key updated successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))
