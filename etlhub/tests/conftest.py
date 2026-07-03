import pytest
from fastapi.testclient import TestClient

from etlhub.main import app
from etlhub.domain.interfaces.task_launcher import TaskLauncher
from etlhub.domain.interfaces.job_repository import JobRepository


@pytest.fixture
def client():
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
    return MockJobRepository()