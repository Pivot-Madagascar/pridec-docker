import os
import sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from etlhub.api.routers.etl_router import router as etl_router
from etlhub.api.routers.forecast_router import router as forecast_router
from etlhub.infrastructure.html_templates import get_home_html

app = FastAPI(
    title="PRIDE-C ETL API",
    description="API for PRIDE-C ETL operations",
    version="1.0.0",
)

app.include_router(etl_router)
app.include_router(forecast_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    return get_home_html()