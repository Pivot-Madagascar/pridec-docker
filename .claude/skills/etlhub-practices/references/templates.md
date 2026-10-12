# Templates from the existing code

Copy these patterns. Replace `new_task` with the job name. Everything below mirrors code that exists today.

## 1. Job entry (`application/use_cases/etl_use_cases.py`)

A Celery ETL job is one line in `ETL_JOBS`: `task_type -> (function, label of the status messages)`.

```python
from etl.scripts.<module> import new_task

ETL_JOBS = {
    ...
    "new_task": (new_task, "new task"),
}
```

`run_etl_job(task_type, job_store, job_id, **kwargs)` runs it through `_execute_etl_job`: stdout/stderr captured into `_JobLogger`, `ETLException(f"{name} failed: {e}") from e` on failure, `job_store.save_logs(job_id, ...)` on success. Also add the job to `domain/pipeline.py` (`PIPELINE`, `RUN_TASKS`).

## 2. Celery task (`infrastructure/tasks.py`) — nothing to add

`task_etl(task_type, job_id, webhook_url=None, **kwargs)` runs every `ETL_JOBS` entry through `_run_task`, and `CeleryTaskLauncher.launch` accepts every `ETL_JOBS` key (plus `forecast`); another key raises `ValueError(f"Unknown task type: {task_type}")`.

What `_run_task` does, so you do not repeat it: status `running` → `run_fn(job_store=..., job_id=...)` → status `success` (+ webhook) or, on exception, append the traceback to the job log, publish an ERROR log, status `error` (+ webhook), then **`raise`**. `task_forecast` also goes through it.

## 3. Service (`application/use_cases/ingestion_service.py`) — nothing to add

`IngestionService.launch(task_type, webhook_url=None, confirm=False, **kwargs)` generates `f"{task_type}_{uuid.uuid4().hex[:8]}"` and calls `task_launcher.launch(...)`.

## 4. Router endpoint (`api/routers/etl/ingest_router.py`)

One entry in the table at the bottom of the file (or an `add_launch_route(router, ...)` call in another router):

```python
("new_task", "Short summary",
 "Launches the task in the background. Executes `etl/scripts/<module>.py` asynchronously. ",
 "Task accepted and queued in background.", "New task started in background"),
```

It registers `POST /new_task` (202, `ETLResponse`, query params `webhook_url` and `confirm`). The `confirm` description is `CONFIRM_RELAUNCH` by default, `CONFIRM_OVERWRITE` (from `api/routers/__init__.py`) for jobs that overwrite forecast inputs. The handler only calls a non-blocking `.delay()`: never put the work itself in it.

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
    monkeypatch.setattr(tasks, "notify_webhook", lambda url, job_id, status, message: sent.append({"status": status}))
    return sent
```

Call the task body with `tasks.task_etl.run(task_type, job_id, webhook_url="http://hook")` (or `tasks.task_forecast.run(...)`) (no broker needed). Assert both the stored record and `webhooks[-1]["status"]`. For failures use `pytest.raises(...)`: the task must re-raise.

Note: `"http://hook"` would be rejected by the webhook validator (M4) if the test goes through a real `CeleryTaskLauncher.launch`. Task-level tests call `.run()` directly and are not affected.

## 9. Patching rules that actually work

- Patch the name **where it is used**: `monkeypatch.setattr(tasks, "JobStore", ...)`, not `etlhub.core.dependencies.get_x` after `Depends` has already bound it.
- Prefer `app.dependency_overrides[...]` for anything injected with `Depends`.
- `etlhub.core.config.get_settings` is imported by name in several modules (e.g. `dhis2_auth.py`). Patching the source module has no effect there; patch the importing module.
- `get_settings()` is `lru_cache`d: clear it (`get_settings.cache_clear()`) when a test changes env vars.
- With Redis mocked, `RequestTracker` falls back to files: each test run writes about 119 `logs/requests/*.json` under the repository root (git-ignored). A fixture that points `LOGS_DIR` to `tmp_path` and calls `get_settings.cache_clear()` would stop it. Not implemented and not tested: a suggestion.
- `_token_cache` in `dhis2_auth.py` is module-global. Clear it in a fixture or tests become order-dependent (see M6 in `migrations.md`).