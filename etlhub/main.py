import os
import sys
from fastapi import Depends, FastAPI, Request
from fastapi.dependencies.utils import get_flat_dependant
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRoute

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
from etlhub.api.routers.pipeline_router import router as pipeline_router
from etlhub.api.auth import auth_router, get_current_user
from etlhub.api.auth.dhis2_auth import SESSION_COOKIE
from etlhub.api.routers import NOT_AUTHENTICATED
from etlhub.domain.exceptions import (
    ETLException, JobNotFoundError, ValidationError, PipelineBlockedError, ConfirmationRequiredError,
)

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


@app.exception_handler(ConfirmationRequiredError)
async def confirmation_required_handler(request: Request, exc: ConfirmationRequiredError):
    return JSONResponse(status_code=409, content={
        "code": "confirmation_required", "message": str(exc), "impact": exc.impact,
    })


@app.exception_handler(PipelineBlockedError)
async def pipeline_blocked_handler(request: Request, exc: PipelineBlockedError):
    return JSONResponse(status_code=409, content={"message": str(exc)})


@app.exception_handler(ETLException)
async def etl_exception_handler(request: Request, exc: ETLException):
    return JSONResponse(status_code=500, content={"message": str(exc)})


# Every router needs a session, except auth (login/logout). The dependency also covers
# the log WebSocket (origin + session, close code 4401).
# tests/api/test_route_protection.py fails if a new route is left open.
_session = {"dependencies": [Depends(get_current_user)], "responses": NOT_AUTHENTICATED}
app.include_router(ingest_router.router, **_session)
app.include_router(analytics_router.router, **_session)
app.include_router(forecast_router, **_session)
app.include_router(tracking_router, **_session)
app.include_router(validation_router, **_session)
app.include_router(forecast_report_router, **_session)
app.include_router(config_router, **_session)
app.include_router(input_router, **_session)
app.include_router(pipeline_router, **_session)
app.include_router(auth_router)


@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def root():
    return "/docs"


def _openapi() -> dict:
    """OpenAPI with the session cookie, marked on exactly the operations that depend on get_current_user."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = FastAPI.openapi(app)
    schema["components"]["securitySchemes"] = {"session": {
        "type": "apiKey", "in": "cookie", "name": SESSION_COOKIE,
        "description": "HttpOnly cookie set by POST /auth/login. In /docs, log in there first: the browser sends it.",
    }}
    for route in app.routes:
        if not (isinstance(route, APIRoute) and route.include_in_schema):
            continue
        if any(d.call is get_current_user for d in get_flat_dependant(route.dependant).dependencies):
            for method in route.methods - {"HEAD"}:
                schema["paths"][route.path][method.lower()]["security"] = [{"session": []}]
    return schema


app.openapi = _openapi