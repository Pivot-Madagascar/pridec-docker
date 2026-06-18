import uuid
from fastapi import APIRouter, HTTPException, Depends

from etlhub.infrastructure.tasks import task_forecast
from etlhub.infrastructure.job_store import JobStore
from etlhub.domain.schemas import ETLResponse, ForecastParams, JobStatus
from etlhub.api.dependencies import get_job_store

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.post(
    "/",
    response_model=ETLResponse,
    status_code=202,
    summary="Launch R forecast pipeline via Docker",
    description=(
        "Starts a new R forecast pipeline inside a Docker container "
        "(`mvevans89/pridec_forecast:latest`). The container is configured "
        "via `ForecastParams` input paths and Docker volume bindings. "
        "Runs asynchronously in the background."
    ),
    response_description="Forecast pipeline accepted and started in background.",
    responses={
        422: {
            "description": "Validation Error - missing or invalid forecast parameters",
        }
    },
)
async def api_forecast(
    params: ForecastParams = Depends(),
    job_store: JobStore = Depends(get_job_store),
):
    job_id = f"forecast_{uuid.uuid4().hex[:8]}"

    forecast_params = {
        "config": params.config_path,
        "external_data": params.external_data_path,
        "climate_data": params.climate_data_path,
        "disease_data": params.disease_data_path,
        "orgUnit_poly": params.orgUnit_poly_path,
    }

    task_forecast.delay(job_id, forecast_params)

    return ETLResponse(
        status="accepted",
        message="Forecast started",
        job_id=job_id
    )


@router.get(
    "/status/{job_id}",
    response_model=JobStatus,
    summary="Get forecast job status",
    description=(
        "Retrieves the current status of a forecast job by its ID. "
        "Status is checked in Redis or the filesystem at `logs/{job_id}.json`. "
    ),
    response_description="Current job status (running, success, or error).",
    responses={
        404: {
            "description": "Job not found - invalid or expired job ID",
            "content": {
                "application/json": {
                    "example": {"detail": "Job not found"}
                }
            },
        }
    },
)
async def forecast_status(
    job_id: str,
    job_store: JobStore = Depends(get_job_store),
):
    status = job_store.get(job_id)
    if status:
        return JobStatus(**status)

    from etlhub.core.config import get_settings
    settings = get_settings()
    status = job_store.load_from_file(job_id, settings.logs_dir)
    if status:
        return JobStatus(**status)

    raise HTTPException(status_code=404, detail="Job not found")