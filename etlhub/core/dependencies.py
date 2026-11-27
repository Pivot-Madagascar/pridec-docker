from functools import lru_cache
from fastapi import Depends

from etlhub.infrastructure.job_store import JobStore
from etlhub.infrastructure.request_tracker import get_request_tracker
from etlhub.infrastructure.checkpoint_store import get_checkpoint_store
from etlhub.infrastructure.default_files import DefaultFiles
from etlhub.infrastructure.tasks import CeleryTaskLauncher
from etlhub.infrastructure import auth_store, etl_events
from etlhub.infrastructure.config_store import ConfigStore
from etlhub.infrastructure.fetched_imports import RedisFetchedImports
from etlhub.infrastructure.dhis2_reader import HttpDHIS2Reader
from etlhub.infrastructure.output_files import WorkDirOutputFiles
from etlhub.infrastructure.dhis2_accounts import HttpDHIS2Accounts
from etlhub.infrastructure.import_settings import ScriptImportSettings

from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.task_launcher import TaskLauncher
from etlhub.domain.interfaces.request_tracker import RequestTrackerProtocol
from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.interfaces.auth_store import AuthStore
from etlhub.domain.interfaces.config_repository import ConfigRepository
from etlhub.domain.interfaces.event_publisher import EventPublisher
from etlhub.domain.interfaces.fetched_imports import FetchedImports
from etlhub.domain.interfaces.dhis2_reader import DHIS2Reader
from etlhub.domain.interfaces.event_subscriber import EventSubscriber
from etlhub.domain.interfaces.output_files import OutputFiles
from etlhub.domain.interfaces.dhis2_accounts import DHIS2Accounts
from etlhub.domain.interfaces.import_settings import ImportSettings

from etlhub.application.use_cases.forecast_service import ForecastService
from etlhub.application.use_cases.analytics_service import AnalyticsService
from etlhub.application.use_cases.ingestion_service import IngestionService
from etlhub.application.use_cases.tracking_service import TrackingService
from etlhub.application.use_cases.input_upload_service import InputUploadService
from etlhub.application.use_cases.journal_service import JournalService
from etlhub.application.use_cases.availability_service import AvailabilityService
from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir


@lru_cache
def get_job_repository() -> JobRepository:
    return JobStore()


def get_request_tracker_repo() -> RequestTrackerProtocol:
    return get_request_tracker()  # the middleware's instance: one tracker per process


@lru_cache
def get_task_launcher() -> TaskLauncher:
    return CeleryTaskLauncher()


# auth_store and etl_events are modules: their functions implement the port (PEP 544 accepts modules).
def get_auth_store() -> AuthStore:
    return auth_store


def get_event_publisher() -> EventPublisher:
    return etl_events


def get_event_subscriber() -> EventSubscriber:
    return etl_events.RedisEventSubscriber()  # one subscription per WebSocket


def get_output_files() -> OutputFiles:
    return WorkDirOutputFiles()


def get_config_store() -> ConfigRepository:
    return ConfigStore()


def get_fetched_imports() -> FetchedImports:
    return RedisFetchedImports()


def get_dhis2_accounts() -> DHIS2Accounts:
    return HttpDHIS2Accounts()  # a new one per login or logout: opened with `with`


def get_pipeline_gate() -> PipelineGate:
    return get_checkpoint_store()


def get_journal_service(
    gate: PipelineGate = Depends(get_pipeline_gate),
    request_tracker: RequestTrackerProtocol = Depends(get_request_tracker_repo),
) -> JournalService:
    return JournalService(gate, request_tracker)


def get_dhis2_reader() -> DHIS2Reader:
    return HttpDHIS2Reader()


def get_import_settings() -> ImportSettings:
    return ScriptImportSettings()


def get_availability_service(gate: PipelineGate = Depends(get_pipeline_gate),
                             dhis2: DHIS2Reader = Depends(get_dhis2_reader),
                             settings: ImportSettings = Depends(get_import_settings)) -> AvailabilityService:
    return AvailabilityService(gate, dhis2, settings)


def get_forecast_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
    job_repo: JobRepository = Depends(get_job_repository),
) -> ForecastService:
    return ForecastService(task_launcher, job_repo)


def get_analytics_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
    gate: PipelineGate = Depends(get_pipeline_gate),
    imports: FetchedImports = Depends(get_fetched_imports),
) -> AnalyticsService:
    return AnalyticsService(task_launcher, gate, imports)


def get_ingestion_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
    settings: ImportSettings = Depends(get_import_settings),
) -> IngestionService:
    return IngestionService(task_launcher, settings)


def get_tracking_service(
    request_tracker: RequestTrackerProtocol = Depends(get_request_tracker_repo),
    job_repo: JobRepository = Depends(get_job_repository),
    gate: PipelineGate = Depends(get_pipeline_gate),
) -> TrackingService:
    return TrackingService(request_tracker, job_repo, gate)


def get_input_upload_service(gate: PipelineGate = Depends(get_pipeline_gate)) -> InputUploadService:
    return InputUploadService(work_dir(get_settings().data_dir, "input", current_test_mode()), gate, DefaultFiles())
