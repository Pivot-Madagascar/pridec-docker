from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends

from etlhub.application.use_cases.forecast_use_cases import start_forecast
from etlhub.domain.schemas import ETLResponse, ForecastParams, JobStatus
from etlhub.infrastructure.job_store import JobStore
from etlhub.api.dependencies import get_job_store
from etlhub.core.config import get_settings

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
    background_tasks: BackgroundTasks,
    params: ForecastParams = Depends(),
    job_store: JobStore = Depends(get_job_store),
):
    return start_forecast(params=params, job_store=job_store, background_tasks=background_tasks)


@router.get(
    "/status/{job_id}",
    response_model=JobStatus,
    summary="Get forecast job status",
    description=(
        "Retrieves the current status of a forecast job by its ID. "
        "Status is checked first in the in-memory `JobStore`, then in "
        "the filesystem at `logs/{job_id}.json`. "
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
        return status

    settings = get_settings()
    status = job_store.load_from_file(job_id, settings.logs_dir)
    if status:
        return JobStatus(**status)

    raise HTTPException(status_code=404, detail="Job not found")
