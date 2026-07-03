import sys
from unittest.mock import MagicMock

sys.modules['redis'] = MagicMock()
sys.modules['pridec_gee'] = MagicMock()
sys.modules['pivot_dhis_tools'] = MagicMock()
sys.modules['earthengine_api'] = MagicMock()
sys.modules['geopandas'] = MagicMock()

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    from etlhub.main import app
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_task_launcher():
    class MockTaskLauncher:
        def launch(self, task_type: str, job_id: str, webhook_url: str | None = None, **kwargs):
            pass
    return MockTaskLauncher()


@pytest.fixture
def mock_job_repository():
    class MockJobRepository:
        def get(self, job_id: str):
            return None
        def load_from_file(self, job_id: str, logs_dir: str):
            return None
        def get_logs(self, job_id: str):
            return None
    return MockJobRepository()


@pytest.fixture
def mock_request_tracker():
    class MockRequestTracker:
        def list_recent(self, limit: int = 50):
            return []
        def get(self, request_id: str):
            return None
    return MockRequestTracker()


@pytest.fixture
def override_dependencies(app, mock_task_launcher, mock_job_repository, mock_request_tracker):
    from etlhub.core.dependencies import get_ingestion_service, get_analytics_service, get_forecast_service, get_tracking_service
    from etlhub.application.use_cases.ingestion_service import IngestionService
    from etlhub.application.use_cases.analytics_service import AnalyticsService
    from etlhub.application.use_cases.forecast_service import ForecastService
    from etlhub.application.use_cases.tracking_service import TrackingService
    
    def get_mock_ingestion_service():
        return IngestionService(mock_task_launcher)
    
    def get_mock_analytics_service():
        return AnalyticsService(mock_task_launcher, mock_job_repository, MagicMock())
    
    def get_mock_forecast_service():
        return ForecastService(mock_task_launcher, mock_job_repository)
    
    def get_mock_tracking_service():
        return TrackingService(mock_request_tracker, mock_job_repository)
    
    app.dependency_overrides[get_ingestion_service] = get_mock_ingestion_service
    app.dependency_overrides[get_analytics_service] = get_mock_analytics_service
    app.dependency_overrides[get_forecast_service] = get_mock_forecast_service
    app.dependency_overrides[get_tracking_service] = get_mock_tracking_service
    
    yield app
    
    app.dependency_overrides.clear()