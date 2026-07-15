from functools import lru_cache
from fastapi import Depends

from etlhub.infrastructure.job_store import JobStore
from etlhub.infrastructure.request_tracker import RequestTracker
from etlhub.infrastructure.tasks import CeleryTaskLauncher, DefaultWebhookNotifier
from etlhub.api.etl_events import get_etl_event_manager

from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.task_launcher import TaskLauncher
from etlhub.domain.interfaces.event_publisher import EventPublisher
from etlhub.domain.interfaces.webhook_notifier import WebhookNotifier
from etlhub.domain.interfaces.request_tracker import RequestTrackerProtocol

from etlhub.application.use_cases.forecast_service import ForecastService
from etlhub.application.use_cases.analytics_service import AnalyticsService
from etlhub.application.use_cases.validation_service import ValidationService
from etlhub.application.use_cases.ingestion_service import IngestionService
from etlhub.application.use_cases.tracking_service import TrackingService


@lru_cache
def get_job_repository() -> JobRepository:
    return JobStore()


@lru_cache
def get_request_tracker_repo() -> RequestTrackerProtocol:
    return RequestTracker()


@lru_cache
def get_task_launcher() -> TaskLauncher:
    return CeleryTaskLauncher()


@lru_cache
def get_webhook_notifier() -> WebhookNotifier:
    return DefaultWebhookNotifier()


def get_forecast_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
    job_repo: JobRepository = Depends(get_job_repository),
) -> ForecastService:
    return ForecastService(task_launcher, job_repo)


def get_analytics_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
    job_repo: JobRepository = Depends(get_job_repository),
    webhook_notifier: WebhookNotifier = Depends(get_webhook_notifier),
) -> AnalyticsService:
    return AnalyticsService(task_launcher, job_repo, webhook_notifier)


def get_validation_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
) -> ValidationService:
    return ValidationService(task_launcher)


def get_ingestion_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
) -> IngestionService:
    return IngestionService(task_launcher)


def get_tracking_service(
    request_tracker: RequestTrackerProtocol = Depends(get_request_tracker_repo),
    job_repo: JobRepository = Depends(get_job_repository),
) -> TrackingService:
    return TrackingService(request_tracker, job_repo)