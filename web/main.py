from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import subprocess
import os
import sys
import logging
import requests
import uuid
import json
from pathlib import Path
from .forecast_runner import run_rscript, JOBS, DATA_DIR, LOGS_DIR

# Set working directory to project root (where .gee-private-key.json lives)
# so ETL scripts can find it via os.getcwd()
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

# Add the parent directory to the Python path to import the etl package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from etl.scripts.import_gee import import_gee
from etl.scripts.import_pivot_COM import import_pivot_com
from etl.scripts.import_pivot_CSB import import_pivot_csb
from etl.scripts.fetch_pridec_climate import fetch_climate
from etl.scripts.fetch_pridec_disease import fetch_disease
from etl.scripts.fetch_pridec_geojson import fetch_geojson
from etl.scripts.build_analytics import build_analytics
from etl.scripts.post_forecast import post_forecast
from etl.scripts.calc_CSB_alerts import calc_csb_alerts
from etl.scripts.update_pridec_key import update_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PRIDE-C ETL API",
    description="API for PRIDE-C ETL operations",
    version="1.0.0"
)

class ETLResponse(BaseModel):
    status: str = ""
    message: str = ""
    job_id: str = ""

@app.get("/")
async def root():
    return {
        "message": "PRIDE-C ETL API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.post("/import_gee", response_model=ETLResponse)
async def api_import_gee(background_tasks: BackgroundTasks):
    background_tasks.add_task(import_gee)
    return ETLResponse(status="accepted", message="Import GEE task started in background")

@app.post("/import_pivot_com", response_model=ETLResponse)
async def api_import_pivot_com(background_tasks: BackgroundTasks):
    background_tasks.add_task(import_pivot_com)
    return ETLResponse(status="accepted", message="Import Pivot COM task started in background")

@app.post("/import_pivot_csb", response_model=ETLResponse)
async def api_import_pivot_csb(background_tasks: BackgroundTasks):
    background_tasks.add_task(import_pivot_csb)
    return ETLResponse(status="accepted", message="Import Pivot CSB task started in background")

@app.post("/fetch_climate", response_model=ETLResponse)
async def api_fetch_climate():
    try:
        os.makedirs("input", exist_ok=True)
        fetch_climate()
        return ETLResponse(status="success", message="Climate data fetched successfully")
    except Exception as e:
        logger.error(f"Error fetching climate data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch climate data: {str(e)}")

@app.post("/fetch_disease", response_model=ETLResponse)
async def api_fetch_disease():
    try:
        os.makedirs("input", exist_ok=True)
        fetch_disease()
        return ETLResponse(status="success", message="Disease data fetched successfully")
    except Exception as e:
        logger.error(f"Error fetching disease data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch disease data: {str(e)}")

@app.post("/fetch_geojson", response_model=ETLResponse)
async def api_fetch_geojson():
    try:
        os.makedirs("input", exist_ok=True)
        fetch_geojson()
        return ETLResponse(status="success", message="GeoJSON data fetched successfully")
    except Exception as e:
        logger.error(f"Error fetching geojson data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch geojson data: {str(e)}")

@app.post("/build_analytics", response_model=ETLResponse)
async def api_build_analytics(background_tasks: BackgroundTasks):
    background_tasks.add_task(build_analytics)
    return ETLResponse(status="accepted", message="Build analytics task started in background")

@app.post("/post_forecast", response_model=ETLResponse)
async def api_post_forecast():
    try:
        post_forecast()
        return ETLResponse(status="success", message="Forecast posted successfully")
    except Exception as e:
        logger.error(f"Error posting forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to post forecast: {str(e)}")

@app.post("/calc_csb_alerts", response_model=ETLResponse)
async def api_calc_csb_alerts(background_tasks: BackgroundTasks):
    background_tasks.add_task(calc_csb_alerts)
    return ETLResponse(status="accepted", message="Calculate CSB alerts task started in background")

@app.post("/update_key", response_model=ETLResponse)
async def api_update_key():
    try:
        update_key()
        return ETLResponse(status="success", message="Key updated successfully")
    except Exception as e:
        logger.error(f"Error updating key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update key: {str(e)}")

@app.post("/forecast", response_model=ETLResponse)
async def api_forecast(
    config_path: str = "input/config.json",
    external_data_path: str = "input/external_data.csv",
    climate_data_path: str = "input/climate_data.json",
    disease_data_path: str = "input/disease_data.json",
    orgUnit_poly_path: str = "input/orgUnit_poly.geojson",
    background_tasks: BackgroundTasks = None
):
    job_id = f"forecast_{uuid.uuid4().hex[:8]}"

    params = {
        "config": config_path,
        "external_data": external_data_path,
        "climate_data": climate_data_path,
        "disease_data": disease_data_path,
        "orgUnit_poly": orgUnit_poly_path,
    }

    background_tasks.add_task(run_rscript, job_id, params)

    return ETLResponse(
        status="accepted",
        message="Forecast started",
        job_id=job_id
    )


@app.get("/forecast/status/{job_id}")
async def forecast_status(job_id: str):
    if job_id in JOBS:
        return JOBS[job_id]

    # Fallback fichier après redémarrage
    status_file = LOGS_DIR / f"{job_id}.json"
    if status_file.exists():
        return json.loads(status_file.read_text())

    return {"status": "not_found", "job_id": job_id}