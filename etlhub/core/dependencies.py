from functools import lru_cache
from pathlib import Path
from fastapi import Depends

from etlhub.infrastructure.job_store import JobStore
from etlhub.infrastructure.request_tracker import RequestTracker
from etlhub.infrastructure.checkpoint_store import get_checkpoint_store
from etlhub.infrastructure.tasks import CeleryTaskLauncher

from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.task_launcher import TaskLauncher
from etlhub.domain.interfaces.request_tracker import RequestTrackerProtocol
from etlhub.domain.interfaces.pipeline_gate import PipelineGate

from etlhub.application.use_cases.forecast_service import ForecastService
from etlhub.application.use_cases.analytics_service import AnalyticsService
from etlhub.application.use_cases.ingestion_service import IngestionService
from etlhub.application.use_cases.tracking_service import TrackingService
from etlhub.application.use_cases.input_upload_service import InputUploadService
from etlhub.core.config import get_settings


@lru_cache
def get_job_repository() -> JobRepository:
    return JobStore()


@lru_cache
def get_request_tracker_repo() -> RequestTrackerProtocol:
    return RequestTracker()


@lru_cache
def get_task_launcher() -> TaskLauncher:
    return CeleryTaskLauncher()


def get_pipeline_gate() -> PipelineGate:
    return get_checkpoint_store()


def get_forecast_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
    job_repo: JobRepository = Depends(get_job_repository),
) -> ForecastService:
    return ForecastService(task_launcher, job_repo)


def get_analytics_service(
    job_repo: JobRepository = Depends(get_job_repository),
    gate: PipelineGate = Depends(get_pipeline_gate),
) -> AnalyticsService:
    return AnalyticsService(job_repo, gate)


def get_ingestion_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
) -> IngestionService:
    return IngestionService(task_launcher)


def get_tracking_service(
    request_tracker: RequestTrackerProtocol = Depends(get_request_tracker_repo),
    job_repo: JobRepository = Depends(get_job_repository),
) -> TrackingService:
    return TrackingService(request_tracker, job_repo)


def get_input_upload_service(gate: PipelineGate = Depends(get_pipeline_gate)) -> InputUploadService:
    return InputUploadService(Path(get_settings().data_dir) / "input", gate)
