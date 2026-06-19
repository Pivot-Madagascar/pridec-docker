import os
import sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "etl", "scripts"))

from etlhub.api.middleware import setup_cors, RequestTrackingMiddleware
from etlhub.api.routers.etl import ingest_router, analytics_router
from etlhub.api.routers.forecast_router import router as forecast_router
from etlhub.api.routers.tracking_router import router as tracking_router
from etlhub.presentation.html_templates import get_home_html

app = FastAPI(
    title="Hub Center API",
    description="Hub Center application",
    version="1.0.0",
)

app.add_middleware(RequestTrackingMiddleware)
setup_cors(app)

app.include_router(ingest_router.router)
app.include_router(analytics_router.router)
app.include_router(forecast_router)
app.include_router(tracking_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    return get_home_html()
