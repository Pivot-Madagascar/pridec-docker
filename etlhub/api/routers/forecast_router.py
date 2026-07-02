from fastapi import APIRouter, HTTPException, Depends

from etlhub.application.use_cases.forecast_service import ForecastService
from etlhub.domain.schemas import ETLResponse, ForecastParams, JobStatus
from etlhub.domain.exceptions import ETLException
from etlhub.core.dependencies import get_forecast_service

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
    params: ForecastParams,
    service: ForecastService = Depends(get_forecast_service),
):
    job_id = service.launch(params)
    return ETLResponse(
        status="accepted",
        message="Forecast started",
        job_id=job_id,
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
    service: ForecastService = Depends(get_forecast_service),
):
    try:
        status = service.get_status(job_id)
        return JobStatus(**status)
    except ETLException:
        raise HTTPException(status_code=404, detail="Job not found")