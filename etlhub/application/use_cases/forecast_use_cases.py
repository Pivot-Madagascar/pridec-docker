import uuid
from fastapi import BackgroundTasks

from etlhub.application.use_cases.etl_use_cases import ETLException
from etlhub.domain.schemas import ETLResponse, ForecastParams
from etlhub.infrastructure.job_store import JobStore
from etlhub.forecast_runner import run_rscript


def start_forecast(
    params: ForecastParams,
    job_store: JobStore,
    background_tasks: BackgroundTasks
) -> ETLResponse:
    job_id = f"forecast_{uuid.uuid4().hex[:8]}"

    forecast_params = {
        "config": params.config_path,
        "external_data": params.external_data_path,
        "climate_data": params.climate_data_path,
        "disease_data": params.disease_data_path,
        "orgUnit_poly": params.orgUnit_poly_path,
    }

    background_tasks.add_task(run_rscript, job_id, forecast_params)

    return ETLResponse(
        status="accepted",
        message="Forecast started",
        job_id=job_id
    )