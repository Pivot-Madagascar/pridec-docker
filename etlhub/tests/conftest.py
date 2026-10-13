import sys
from unittest.mock import MagicMock

redis_mock = MagicMock()
redis_mock.asyncio = MagicMock()
# `except redis.RedisError` needs a real exception class, not a MagicMock.
redis_mock.RedisError = type("RedisError", (Exception,), {})
sys.modules['redis'] = redis_mock
sys.modules['redis.asyncio'] = redis_mock.asyncio
sys.modules['pridec_gee'] = MagicMock()
sys.modules['pivot_dhis_tools'] = MagicMock()
sys.modules['earthengine_api'] = MagicMock()
sys.modules['geopandas'] = MagicMock()

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _request_log_db(tmp_path, monkeypatch):
    from etlhub.infrastructure import request_tracker
    monkeypatch.setattr(request_tracker, "_request_tracker", request_tracker.RequestTracker(tmp_path / "etlhub.db"))


@pytest.fixture(autouse=True)
def checkpoint_store(tmp_path, monkeypatch):
    """The real pipeline gate, on a temporary db: launches never touch logs/etlhub.db."""
    from etlhub.infrastructure import checkpoint_store as module
    # data_dir = tmp_path: input/ and output/ are emptied when a run opens, uploads/ keeps the uploaded files.
    mode = {"dry_run": False}  # production by default; tests switch it through store.set_mode or mode[...]
    store = module.CheckpointStore(
        tmp_path / "etlhub.db", data_dir=tmp_path, apply_context=lambda ctx: store.contexts.append(ctx),
        dry_run=lambda: mode["dry_run"], set_dry_run=lambda value: mode.update(dry_run=value), blob=FakeBlob(),
    )
    store.contexts = []  # run contexts the jobs received (instead of Redis)
    store.mode = mode
    monkeypatch.setattr(module, "_checkpoint_store", store)
    return store


class FakeBlob:
    """Redis key of the test-mode checkpoint db, in memory."""

    def __init__(self):
        self.data = None

    def get(self):
        return self.data

    def set(self, data):
        self.data = data

    def delete(self):
        self.data = None

    def lock(self):
        from contextlib import nullcontext
        return nullcontext()


class OpenGate:
    """Pipeline gate that lets everything through: for tests that are not about the pipeline order."""

    def start(self, task, job_id, confirm=False):
        pass

    def finish(self, job_id, status):
        pass

    @contextmanager
    def run(self, task, job_id, confirm=False):
        yield

    @contextmanager
    def change_input(self, name, confirm=False, removed=False):
        yield

    def launch_cycle(self):
        from etlhub.domain.pipeline import this_month
        return this_month()


TEST_USER = {"id": "u1", "email": None, "username": "tester", "displayName": "Tester", "is_admin": True}


@pytest.fixture
def app():
    """The app with a logged-in user: router tests are not about authentication."""
    from etlhub.main import app
    from etlhub.api.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield app
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def anon_app():
    """The app with the real session check (no override)."""
    from etlhub.main import app
    from etlhub.api.auth import get_current_user
    app.dependency_overrides.pop(get_current_user, None)
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
        def list_recent(self, limit: int = 50, endpoint: str | None = None):
            return []
        def get(self, request_id: str):
            return None
        def save(self, log: dict):
            pass
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
        return AnalyticsService(mock_job_repository, OpenGate())
    
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


class FakePubSub:
    """Async pub/sub double for the log WebSocket: tests push messages into `queue`."""

    def __init__(self, store):
        self.store = store
        self.channels = []
        self.closed = False

    async def subscribe(self, *channels):
        self.channels.extend(channels)

    async def get_message(self, ignore_subscribe_messages=True, timeout=0.0):
        import asyncio
        if self.store.queue:
            return {"type": "message", "data": self.store.queue.pop(0)}
        await asyncio.sleep(0.01)
        return None

    async def unsubscribe(self, *channels):
        self.channels = []

    async def aclose(self):
        self.closed = True


class FakeAsyncRedis:
    def __init__(self):
        self.data = {}
        self.queue = []
        self.pubsubs = []

    async def get(self, key):
        return self.data.get(key)

    def pubsub(self):
        ps = FakePubSub(self)
        self.pubsubs.append(ps)
        return ps


@pytest.fixture
def fake_ws_redis(monkeypatch, tmp_path):
    """Replaces the WebSocket's Redis client; job log files are looked up in tmp_path."""
    from types import SimpleNamespace
    from etlhub.api.websockets import etl_logs
    fake = FakeAsyncRedis()

    async def client():
        return fake

    monkeypatch.setattr(etl_logs, "get_redis_client", client)
    monkeypatch.setattr(etl_logs, "get_settings", lambda: SimpleNamespace(logs_dir=str(tmp_path)))
    return fake
