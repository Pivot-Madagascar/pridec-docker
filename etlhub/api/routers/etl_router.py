from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends

from etlhub.application.use_cases.etl_use_cases import (
    ETLException,
    run_import_gee,
    run_import_pivot_com,
    run_import_pivot_csb,
    run_fetch_climate,
    run_fetch_disease,
    run_fetch_geojson,
    run_build_analytics,
    run_post_forecast,
    run_calc_csb_alerts,
    run_update_key,
)
from etlhub.domain.schemas import ETLResponse
from etlhub.infrastructure.job_store import JobStore
from etlhub.api.dependencies import get_job_store

router = APIRouter(prefix="", tags=["ETL"])


@router.post("/import_gee", response_model=ETLResponse)
async def api_import_gee(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_import_gee)
    return ETLResponse(status="accepted", message="Import GEE task started in background")


@router.post("/import_pivot_com", response_model=ETLResponse)
async def api_import_pivot_com(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_import_pivot_com)
    return ETLResponse(status="accepted", message="Import Pivot COM task started in background")


@router.post("/import_pivot_csb", response_model=ETLResponse)
async def api_import_pivot_csb(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_import_pivot_csb)
    return ETLResponse(status="accepted", message="Import Pivot CSB task started in background")


@router.post("/fetch_climate", response_model=ETLResponse)
async def api_fetch_climate():
    try:
        run_fetch_climate()
        return ETLResponse(status="success", message="Climate data fetched successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch_disease", response_model=ETLResponse)
async def api_fetch_disease():
    try:
        run_fetch_disease()
        return ETLResponse(status="success", message="Disease data fetched successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch_geojson", response_model=ETLResponse)
async def api_fetch_geojson():
    try:
        run_fetch_geojson()
        return ETLResponse(status="success", message="GeoJSON data fetched successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))


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