import os
import sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from etlhub.api.middleware import setup_cors
from etlhub.api.routers.etl import ingest_router, analytics_router
from etlhub.api.routers.forecast_router import router as forecast_router
from etlhub.presentation.html_templates import get_home_html

app = FastAPI(
    title="PRIDE-C ETL API",
    description="API for PRIDE-C ETL operations",
    version="1.0.0",
)

setup_cors(app)

app.include_router(ingest_router.router)
app.include_router(analytics_router.router)
app.include_router(forecast_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    return get_home_html()
