import os
import sys
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "etl", "scripts"))

from etlhub.api.middleware import setup_cors, check_origin, RequestTrackingMiddleware
from etlhub.api.routers.etl import ingest_router, analytics_router
from etlhub.api.routers.etl.validation_router import router as validation_router
from etlhub.api.routers.forecast_router import router as forecast_router
from etlhub.api.routers.tracking_router import router as tracking_router
from etlhub.api.routers.forecast_report_router import router as forecast_report_router
from etlhub.api.routers.config_router import router as config_router
from etlhub.api.routers.input_router import router as input_router
from etlhub.api.auth import auth_router, get_current_user
from etlhub.presentation.html_templates import get_home_html
from etlhub.domain.exceptions import ETLException, JobNotFoundError, ValidationError, TaskLaunchError

app = FastAPI(
    title="Hub Center API",
    description="Hub Center application",
    version="1.0.0",
)

app.add_middleware(RequestTrackingMiddleware)
app.middleware("http")(check_origin)
setup_cors(app)

@app.exception_handler(JobNotFoundError)
async def job_not_found_handler(request: Request, exc: JobNotFoundError):
    return JSONResponse(status_code=404, content={"message": "Job not found"})


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content={"message": str(exc)})


@app.exception_handler(TaskLaunchError)
async def task_launch_error_handler(request: Request, exc: TaskLaunchError):
    return JSONResponse(status_code=500, content={"message": str(exc)})


@app.exception_handler(ETLException)
async def etl_exception_handler(request: Request, exc: ETLException):
    return JSONResponse(status_code=500, content={"message": str(exc)})


# Every router needs a session, except auth (login/logout). The dependency also covers
# the log WebSocket (origin + session, close code 4401).
# tests/api/test_route_protection.py fails if a new route is left open.
_session = [Depends(get_current_user)]
app.include_router(ingest_router.router, dependencies=_session)
app.include_router(analytics_router.router, dependencies=_session)
app.include_router(forecast_router, dependencies=_session)
app.include_router(tracking_router, dependencies=_session)
app.include_router(validation_router, dependencies=_session)
app.include_router(forecast_report_router, dependencies=_session)
app.include_router(config_router, dependencies=_session)
app.include_router(input_router, dependencies=_session)
app.include_router(auth_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    return get_home_html()