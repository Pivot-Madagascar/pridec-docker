from fastapi import APIRouter, BackgroundTasks, HTTPException

from etlhub.application.use_cases.etl_use_cases import (
    ETLException,
    run_import_gee,
    run_import_pivot_com,
    run_import_pivot_csb,
    run_fetch_climate,
    run_fetch_disease,
    run_fetch_geojson,
)
from etlhub.domain.schemas import ETLResponse
from etlhub.api.dependencies import get_job_store

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
    summary="Fetch climate data from external source",
    description=(
        "Synchronously fetches climate data from the external source. "
        "Executes `etl/scripts/fetch_pridec_climate.py`. "
    ),
    response_description="Climate data fetched successfully.",
    responses={
        500: {
            "description": "Internal Server Error - fetch failed",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ETLResponse"},
                    "example": {"status": "error", "message": "fetch_pridec_climate failed: ..."},
                }
            },
        }
    },
)
async def api_fetch_climate():
    try:
        run_fetch_climate()
        return ETLResponse(status="success", message="Climate data fetched successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/fetch_disease",
    response_model=ETLResponse,
    summary="Fetch disease data from external source",
    description=(
        "Synchronously fetches disease data from the external source. "
        "Executes `etl/scripts/fetch_pridec_disease.py`. "
    ),
    response_description="Disease data fetched successfully.",
    responses={
        500: {
            "description": "Internal Server Error - fetch failed",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ETLResponse"},
                    "example": {"status": "error", "message": "fetch_pridec_disease failed: ..."},
                }
            },
        }
    },
)
async def api_fetch_disease():
    try:
        run_fetch_disease()
        return ETLResponse(status="success", message="Disease data fetched successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/fetch_geojson",
    response_model=ETLResponse,
    summary="Fetch GeoJSON data from external source",
    description=(
        "Synchronously fetches GeoJSON boundary data from the external source. "
        "Executes `etl/scripts/fetch_pridec_geojson.py`. "
    ),
    response_description="GeoJSON data fetched successfully.",
    responses={
        500: {
            "description": "Internal Server Error - fetch failed",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ETLResponse"},
                    "example": {"status": "error", "message": "fetch_pridec_geojson failed: ..."},
                }
            },
        }
    },
)
async def api_fetch_geojson():
    try:
        run_fetch_geojson()
        return ETLResponse(status="success", message="GeoJSON data fetched successfully")
    except ETLException as e:
        raise HTTPException(status_code=500, detail=str(e))
