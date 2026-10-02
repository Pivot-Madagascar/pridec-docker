# Templates from the existing code

Copy these patterns. Replace `new_task` with the job name. Everything below mirrors code that exists today.

## 1. Service method (`application/use_cases/ingestion_service.py`)

```python
import uuid

from etlhub.domain.interfaces.task_launcher import TaskLauncher


class IngestionService:
    def __init__(self, task_launcher: TaskLauncher):
        self._task_launcher = task_launcher

    def new_task(self, webhook_url: str | None = None) -> str:
        job_id = f"new_task_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("new_task", job_id, webhook_url=webhook_url)
        return job_id
```

The port (`domain/interfaces/task_launcher.py`):

```python
@runtime_checkable
class TaskLauncher(Protocol):
    def launch(self, task_type: str, job_id: str, webhook_url: str | None = None, **kwargs) -> None: ...
```

## 2. Use case wrapper (`application/use_cases/etl_use_cases.py`)

```python
def run_new_task(job_store=None, job_id=None) -> None:
    _execute_etl_job(new_task_fn, job_store=job_store, job_id=job_id, name="new_task")
```

`_execute_etl_job` captures stdout/stderr into `_JobLogger`, raises `ETLException(f"{name} failed: {e}") from e`, then calls `job_store.save_logs(job_id, buf.getvalue())`.

Import the script function at the top of the file with the others: `from etl.scripts.<module> import <fn>`.

## 3. Celery task and registry (`infrastructure/tasks.py`)

```python
@celery_app.task(bind=True)
def task_new_task(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "Task description", run_new_task, webhook_url=webhook_url)
```

```python
class CeleryTaskLauncher:
    def __init__(self):
        self._registry = {
            ...
            "new_task": task_new_task,
        }
```

`launch` raises `ValueError(f"Unknown task type: {task_type}")` when the key is missing, so a forgotten registry entry fails at request time.

What `_run_task` already does, so you do not repeat it: status `running` → `run_fn(job_store=..., job_id=...)` → status `success` (+ webhook) or, on exception, save traceback, publish ERROR log, status `error` (+ webhook), then **`raise`**. Do not write a new task body by hand. (`task_forecast` does, and it is the known duplication.)

## 4. Router endpoint (`api/routers/etl/ingest_router.py`)

```python
@router.post(
    "/new_task",
    response_model=ETLResponse,
    status_code=202,
    summary="Short summary",
    description=(
        "Launches the task in the background. "
        "Executes `etl/scripts/<module>.py` asynchronously. "
        "Pass `webhook_url` to be notified when the job completes."
    ),
    response_description="Task accepted and queued in background.",
)
async def api_new_task(
    webhook_url: str | None = Query(None),
    service: IngestionService = Depends(get_ingestion_service),
):
    job_id = service.new_task(webhook_url)
    return ETLResponse(
        status="accepted",
        message="New task started in background",
        job_id=job_id,
        webhook_url=webhook_url,
    )
```

The handler is `async def` but only calls a non-blocking `.delay()`. That is the only reason it is safe. Never put the work itself in the handler.

## 5. Dependency providers (`core/dependencies.py`)

```python
@lru_cache
def get_task_launcher() -> TaskLauncher:
    return CeleryTaskLauncher()


def get_forecast_service(
    task_launcher: TaskLauncher = Depends(get_task_launcher),
    job_repo: JobRepository = Depends(get_job_repository),
) -> ForecastService:
    return ForecastService(task_launcher, job_repo)
```

New service = new `get_<x>_service` here, and a matching override in `tests/conftest.py::override_dependencies`.

## 6. Auth dependency (`api/auth/dhis2_auth.py`)

`get_current_user` is an `async` dependency using `HTTPBearer(auto_error=False)`. It returns the DHIS2 user dict or raises 401. It is applied per endpoint today:

```python
@router.get("/", response_model=ConfigResponse, dependencies=[Depends(get_current_user)])
```

Import it from `etlhub.api.auth` (exported there) or `etlhub.api.auth.dhis2_auth`.

## 7. Router test (`tests/api/test_ingest_router.py`)

```python
def test_import_gee_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app

    client = TestClient(app)
    response = client.post("/import_gee")
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data
```

If auth is added (M1), the fixture also needs:
`app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}`.

## 8. Celery task test (`tests/infrastructure/test_forecast_task.py`)

```python
class InMemoryJobStore:
    records: dict = {}
    def get(self, job_id):
        record = self.records.get(job_id)
        return dict(record) if record else None
    def set(self, job_id, data):
        self.records[job_id] = dict(data)
    def save_logs(self, job_id, logs):
        pass


@pytest.fixture
def job_store(monkeypatch):
    InMemoryJobStore.records = {}
    monkeypatch.setattr(tasks, "JobStore", InMemoryJobStore)
    return InMemoryJobStore()


@pytest.fixture
def webhooks(monkeypatch):
    sent = []
    monkeypatch.setattr(tasks, "_send_webhook", lambda url, **kwargs: sent.append(kwargs))
    return sent
```

Call the task body with `tasks.task_xxx.run(job_id, ..., webhook_url="http://hook")` (no broker needed). Assert both the stored record and `webhooks[-1]["status"]`. For failures use `pytest.raises(...)`: the task must re-raise.

Note: `"http://hook"` would be rejected by the webhook validator (M4) if the test goes through a real `CeleryTaskLauncher.launch`. Task-level tests call `.run()` directly and are not affected.

## 9. Patching rules that actually work

- Patch the name **where it is used**: `monkeypatch.setattr(tasks, "JobStore", ...)`, not `etlhub.core.dependencies.get_x` after `Depends` has already bound it.
- Prefer `app.dependency_overrides[...]` for anything injected with `Depends`.
- `etlhub.core.config.get_settings` is imported by name in several modules (e.g. `dhis2_auth.py`). Patching the source module has no effect there; patch the importing module.
- `get_settings()` is `lru_cache`d: clear it (`get_settings.cache_clear()`) when a test changes env vars.
- `_token_cache` in `dhis2_auth.py` is module-global. Clear it in a fixture or tests become order-dependent (see M6 in `migrations.md`).