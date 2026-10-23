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
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


def use_instance(monkeypatch, getter, module, cls_name, instance):
    """Fills the lru_cache of a singleton getter with `instance` (callers imported the getter itself, so it cannot be patched).

    The fixture using it clears the cache on teardown.
    """
    getter.cache_clear()
    with monkeypatch.context() as m:
        m.setattr(module, cls_name, lambda: instance)
        getter()
    return instance


@pytest.fixture(name="use_instance")
def use_instance_fixture():
    return use_instance


@pytest.fixture(autouse=True)
def _request_log_db(tmp_path, monkeypatch):
    from etlhub.infrastructure import request_tracker
    use_instance(monkeypatch, request_tracker.get_request_tracker, request_tracker, "RequestTracker",
                 request_tracker.RequestTracker(tmp_path / "etlhub.db"))
    yield
    request_tracker.get_request_tracker.cache_clear()


@pytest.fixture(autouse=True)
def checkpoint_store(tmp_path, monkeypatch):
    """The real pipeline gate, on a temporary db: launches never touch logs/etlhub.db."""
    from etlhub.infrastructure import checkpoint_store as module
    # data_dir = tmp_path: input/ and output/ are emptied when a run opens, uploads/ keeps the uploaded files.
    mode = {"test_mode": False, "dry_run": True}  # production by default; tests switch it through store.set_mode or mode[...]
    store = module.CheckpointStore(
        tmp_path / "etlhub.db", data_dir=tmp_path, apply_context=lambda ctx: store.contexts.append(ctx),
        test_mode=lambda: mode["test_mode"], set_test_mode=lambda value: mode.update(test_mode=value),
        dry_run=lambda: mode["dry_run"], blob=FakeBlob(),
    )
    store.contexts = []  # run contexts the jobs received (instead of Redis)
    store.mode = mode
    use_instance(monkeypatch, module.get_checkpoint_store, module, "CheckpointStore", store)
    yield store
    module.get_checkpoint_store.cache_clear()


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


class FakeJobStore:
    """JobStore in two dicts: job records and job logs."""

    def __init__(self):
        self.records, self.logs = {}, {}

    def get(self, job_id):
        record = self.records.get(job_id)
        return dict(record) if record else None

    def set(self, job_id, data):
        self.records[job_id] = dict(data)

    def append_logs(self, job_id, text):
        self.logs[job_id] = self.logs.get(job_id, "") + text

    def get_logs(self, job_id):
        return self.logs.get(job_id)

    def load_from_file(self, job_id, logs_dir):
        return None


@pytest.fixture
def job_store():
    return FakeJobStore()


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
def override_dependencies(app, mock_task_launcher, job_store, mock_request_tracker):
    from etlhub.core.dependencies import get_ingestion_service, get_analytics_service, get_forecast_service, get_tracking_service
    from etlhub.application.use_cases.ingestion_service import IngestionService
    from etlhub.application.use_cases.analytics_service import AnalyticsService
    from etlhub.application.use_cases.forecast_service import ForecastService
    from etlhub.application.use_cases.tracking_service import TrackingService
    
    def get_mock_ingestion_service():
        return IngestionService(mock_task_launcher)
    
    def get_mock_analytics_service():
        return AnalyticsService(job_store, OpenGate(), SimpleNamespace(publish_log=lambda *a, **k: None,
                                                                       publish_status=lambda *a, **k: None))
    
    def get_mock_forecast_service():
        return ForecastService(mock_task_launcher, job_store)
    
    def get_mock_tracking_service():
        return TrackingService(mock_request_tracker, job_store)
    
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

    def pubsub(self):
        ps = FakePubSub(self)
        self.pubsubs.append(ps)
        return ps


@pytest.fixture
def fake_ws_redis(monkeypatch, tmp_path):
    """Replaces the WebSocket's pub/sub client and JobStore's Redis (both read `fake.data`); log files in tmp_path."""
    from types import SimpleNamespace
    from etlhub.api.websockets import etl_logs
    from etlhub.infrastructure import job_store
    fake = FakeAsyncRedis()

    async def client():
        return fake

    monkeypatch.setattr(etl_logs, "get_redis_client", client)
    monkeypatch.setattr(job_store, "get_redis", lambda: SimpleNamespace(get=fake.data.get))
    monkeypatch.setattr(job_store, "get_settings", lambda: SimpleNamespace(logs_dir=str(tmp_path)))
    return fake
