from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends

from etlhub.application.use_cases.forecast_use_cases import start_forecast
from etlhub.domain.schemas import ETLResponse, ForecastParams, JobStatus
from etlhub.infrastructure.job_store import JobStore
from etlhub.api.dependencies import get_job_store
from etlhub.core.config import get_settings

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.post("/", response_model=ETLResponse)
async def api_forecast(
    background_tasks: BackgroundTasks,
    params: ForecastParams = Depends(),
    job_store: JobStore = Depends(get_job_store),
):
    return start_forecast(params=params, job_store=job_store, background_tasks=background_tasks)


@router.get("/status/{job_id}", response_model=JobStatus)
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