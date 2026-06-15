from fastapi import APIRouter, BackgroundTasks

from hubcenter.application.use_cases.etl_use_cases import (
    ETLException,
    run_import_gee,
    run_import_pivot_com,
    run_import_pivot_csb,
    run_fetch_climate,
    run_fetch_disease,
    run_fetch_geojson,
)
from hubcenter.domain.schemas import ETLResponse
from hubcenter.api.dependencies import get_job_store

router = APIRouter(tags=["Ingest"])


@router.post(
    "/import_gee",
    response_model=ETLResponse,
    status_code=202,
    summary="Import GEE data into DHIS2",
    description=(
        "Launches the GEE import process in the background. "
        "Executes `etl/scripts/import_gee.py` asynchronously. "
    ),
    response_description="Task accepted and queued in background.",
)
async def api_import_gee(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_import_gee)
    return ETLResponse(status="accepted", message="Import GEE task started in background")


@router.post(
    "/import_pivot_com",
    response_model=ETLResponse,
    status_code=202,
    summary="Import Pivot COM data into DHIS2",
    description=(
        "Launches the Pivot COM historical data import in the background. "
        "Executes `etl/scripts/import_pivot_COM.py` asynchronously. "
    ),
    response_description="Task accepted and queued in background.",
)
async def api_import_pivot_com(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_import_pivot_com)
    return ETLResponse(status="accepted", message="Import Pivot COM task started in background")


@router.post(
    "/import_pivot_csb",
    response_model=ETLResponse,
    status_code=202,
    summary="Import Pivot CSB data into DHIS2",
    description=(
        "Launches the Pivot CSB historical data import in the background. "
        "Executes `etl/scripts/import_pivot_CSB.py` asynchronously. "
    ),
    response_description="Task accepted and queued in background.",
)
async def api_import_pivot_csb(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_import_pivot_csb)
    return ETLResponse(status="accepted", message="Import Pivot CSB task started in background")


@router.post(
    "/fetch_climate",
    response_model=ETLResponse,
    status_code=202,
    summary="Fetch climate data from external source",
    description=(
        "Launches the climate data fetch in the background. "
        "Executes `etl/scripts/fetch_pridec_climate.py` asynchronously. "
    ),
    response_description="Climate data fetch accepted and queued in background.",
)
async def api_fetch_climate(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_fetch_climate)
    return ETLResponse(status="accepted", message="Fetch climate task started in background")


@router.post(
    "/fetch_disease",
    response_model=ETLResponse,
    status_code=202,
    summary="Fetch disease data from external source",
    description=(
        "Launches the disease data fetch in the background. "
        "Executes `etl/scripts/fetch_pridec_disease.py` asynchronously. "
    ),
    response_description="Disease data fetch accepted and queued in background.",
)
async def api_fetch_disease(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_fetch_disease)
    return ETLResponse(status="accepted", message="Fetch disease task started in background")


@router.post(
    "/fetch_geojson",
    response_model=ETLResponse,
    status_code=202,
    summary="Fetch GeoJSON data from external source",
    description=(
        "Launches the GeoJSON boundary data fetch in the background. "
        "Executes `etl/scripts/fetch_pridec_geojson.py` asynchronously. "
    ),
    response_description="GeoJSON data fetch accepted and queued in background.",
)
async def api_fetch_geojson(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_fetch_geojson)
    return ETLResponse(status="accepted", message="Fetch geojson task started in background")
