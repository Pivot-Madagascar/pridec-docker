from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
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
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PRIDE-C ETL</title>
  <style>
    :root {
      --amazon-dark: #131921;
      --amazon-orange: #febd69;
      --amazon-light: #f3f3f3;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
      background-color: #f3f4f6;
      color: #111827;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    body.dark {
      background-color: #111827;
      color: #f9fafb;
    }
    /* Header */
    header {
      background-color: var(--amazon-dark);
      color: #ffffff;
      padding: 1rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    header h1 { font-size: 1.125rem; font-weight: 700; }
    header .header-right { display: flex; align-items: center; gap: 1rem; }
    .env-badge {
      background-color: var(--amazon-orange);
      color: var(--amazon-dark);
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.125rem 0.5rem;
      border-radius: 0.25rem;
    }
    .dark-mode-btn {
      padding: 0.25rem 0.75rem;
      border-radius: 0.375rem;
      border: none;
      cursor: pointer;
      font-size: 0.875rem;
      background-color: var(--amazon-light);
      color: #111827;
    }
    body.dark .dark-mode-btn { background-color: #374151; color: #f9fafb; }

    /* Main */
    main {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }
    .card {
      width: 100%;
      max-width: 28rem;
      background: #ffffff;
      border-radius: 1rem;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    body.dark .card { background: #1f2937; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.4); }
    .card-title { text-align: center; }
    .card-title h2 { font-size: 1.875rem; font-weight: 700; color: var(--amazon-dark); }
    body.dark .card-title h2 { color: #f9fafb; }
    .card-title p { margin-top: 0.5rem; font-size: 0.875rem; color: #6b7280; }
    body.dark .card-title p { color: #9ca3af; }

    /* Buttons */
    .btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      width: 100%;
      padding: 0.75rem 1rem;
      border-radius: 0.5rem;
      font-weight: 600;
      font-size: 1rem;
      text-decoration: none;
      cursor: pointer;
      border: none;
      transition: background-color 0.2s;
    }
    .btn-orange {
      background-color: var(--amazon-orange);
      color: var(--amazon-dark);
    }
    .btn-orange:hover { background-color: #f59e0b; }
    .btn-blue { background-color: #2563eb; color: #ffffff; }
    .btn-blue:hover { background-color: #1d4ed8; }
    .btn-gray {
      background-color: #f3f4f6;
      color: #374151;
      font-size: 0.875rem;
    }
    .btn-gray:hover { background-color: #e5e7eb; }
    body.dark .btn-gray { background-color: #374151; color: #e5e7eb; }
    body.dark .btn-gray:hover { background-color: #4b5563; }

    /* Divider */
    .divider {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      width: 100%;
    }
    .divider::before, .divider::after {
      content: '';
      flex: 1;
      height: 1px;
      background-color: #d1d5db;
    }
    body.dark .divider::before, body.dark .divider::after { background-color: #4b5563; }
    .divider span { font-size: 0.75rem; color: #9ca3af; white-space: nowrap; }

    /* Secondary grid */
    .secondary-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }
  </style>
</head>
<body>
  <header>
    <h1>PRIDE-C ETL</h1>
    <div class="header-right">
      <span class="env-badge">Environment: Development</span>
      <button class="dark-mode-btn" onclick="toggleDarkMode()" id="darkModeBtn">Dark Mode</button>
    </div>
  </header>
  <main>
    <div class="card">
      <div class="card-title">
        <h2>Welcome to PRIDE-C ETL</h2>
        <p>Data ingestion and forecasting platform for malaria surveillance</p>
      </div>
      <div style="display:flex;flex-direction:column;gap:0.75rem;">
        <a href="/data-fetch" class="btn btn-orange">
          <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          Fetch Data
        </a>
        <a href="/forecasting" class="btn btn-blue">
          <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          Run Forecast
        </a>
      </div>
        <div class="divider"><span>More options</span></div>
        <div class="secondary-grid">
          <a href="/reports" class="btn btn-gray">Reports</a>
          <a href="/forecast-post" class="btn btn-gray">Post Forecast</a>
        </div>
        <div class="secondary-grid">
          <a href="/docs" class="btn btn-gray">API Docs</a>
          <a href="/login" class="btn btn-gray" style="color:#2563eb;">Log In</a>
        </div>
    </div>
  </main>
  <script>
    function toggleDarkMode() {
      document.body.classList.toggle('dark');
      const btn = document.getElementById('darkModeBtn');
      btn.textContent = document.body.classList.contains('dark') ? 'Light Mode' : 'Dark Mode';
    }
  </script>
</body>
</html>
""")

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