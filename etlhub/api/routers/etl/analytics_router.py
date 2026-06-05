from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends

from etlhub.application.use_cases.etl_use_cases import (
    ETLException,
    run_build_analytics,
    run_post_forecast,
    run_calc_csb_alerts,
    run_update_key,
)
from etlhub.domain.schemas import ETLResponse
from etlhub.api.dependencies import get_job_store

router = APIRouter(tags=["Analytics"])


@router.post("/build_analytics", response_model=ETLResponse)
async def api_build_analytics(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_build_analytics)
    return ETLResponse(status="accepted", message="Build analytics task started in background")


@router.post("/post_forecast", response_model=ETLResponse)
async def api_post_forecast():
    try:
        run_post_forecast()
        return ETLResponse(status="success", message="Forecast posted successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calc_csb_alerts", response_model=ETLResponse)
async def api_calc_csb_alerts(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_calc_csb_alerts)
    return ETLResponse(status="accepted", message="Calculate CSB alerts task started in background")


@router.post("/update_key", response_model=ETLResponse)
async def api_update_key():
    try:
        run_update_key()
        return ETLResponse(status="success", message="Key updated successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))
