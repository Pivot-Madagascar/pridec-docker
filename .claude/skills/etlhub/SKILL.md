---
name: etlhub
description: "How the etlhub FastAPI service (Hub Center API, PRIDE-C) is built and how it behaves today: hexagonal layers, async job lifecycle (Celery + Redis + WebSocket logs), config and Redis keys, DHIS2 auth, the R forecast pipeline run through Docker, endpoints, commands to run and test it. Use whenever a task touches etlhub: adding an ETL endpoint or job type, a Celery task, the forecast pipeline, job tracking (job_store, request_tracker), Redis state, dynamic configuration, DHIS2 authentication, the layers, or the tests. Read it before changing anything, even if the user does not name ETLHub. For HOW to change code well (templates, missing best practices, checklists) use the etlhub-practices skill."
metadata:
  version: 1.1.0
---

# etlhub — how it is built

FastAPI service (port **8111**) that exposes the PRIDE-C ETL scripts (`etl/scripts/*.py`) and the R forecast pipeline through **Celery + Redis**. Consumed by the Vue front-end `etlui`.

This skill describes **what exists and what is true today**, including the rough edges. For code templates, missing best practices and checklists, use `etlhub-practices`. Endpoint, config and Redis tables are in `references/reference.md`.

## Layers

```
etlhub/
├── main.py                 # app composition, exception handlers, routers; sys.path / os.chdir setup
├── core/                   # config.py, dependencies.py (composition root), celery_app.py
├── domain/                 # exceptions.py, interfaces/ (Protocol ports), schemas/ (Pydantic DTOs)
├── application/use_cases/  # *_service.py, etl_use_cases.py, validation_use_cases.py
├── infrastructure/         # tasks.py, job_store.py, request_tracker.py, config_store.py, forecast_runner.py
├── api/                    # routers/, websockets/etl_logs.py, auth/, middleware.py, etl_events.py
├── presentation/           # static HTML landing page
└── tests/                  # api/ and infrastructure/
```

Target direction of imports: `api` → `application`, `core` · `application` → `domain` · `infrastructure` → `domain`, `application` · `domain` → nothing. Adapters are singletons (`@lru_cache`) in `core/dependencies.py`; services are built per request with `Depends()`.

**The code does not fully respect this.** `application` (`etl_use_cases.py`, `validation_use_cases.py`) and `infrastructure` (`tasks.py`, `forecast_runner.py`) import `etlhub.api.etl_events` directly; the `EventPublisher` port exists but is never injected. `core/dependencies.py` has an unused `api` import, and `config_router.py` / `middleware.py` use `infrastructure` without DI. Do not add new violations; the list is in `etlhub/docs/known-issues.md`.

## Coupling with the rest of the repo

- `etl/scripts/*` is **imported in-process** (`from etl.scripts.<module> import <fn>`), made possible by `sys.path.insert` in `main.py` and `validation_use_cases.py`. `main.py` also calls `os.chdir` to the repo root, and scripts write under `os.getcwd()/input|output` (the worker's cwd is unverified).
- The coupling is **two-way**: `etl/scripts/config.py` imports `etlhub.infrastructure.config_store.ConfigStore`. Do not move or rename these modules.
- `forecast/` (R) is run by `docker run` from the worker. Files are exchanged through `input/` and `output/`.
- `etlui` consumes REST + WebSocket. Its contracts are frozen (see `CLAUDE.md`).

## Job lifecycle

```
UI → POST /import_gee?webhook_url=…
  → router → service.import_gee(webhook_url)
      job_id = "import_gee_<8 hex>"          # generated in the service
      task_launcher.launch("import_gee", job_id, webhook_url=…)
  → router → 202 {status: accepted, job_id}
UI → WS /api/tracking/etl-logs/{job_id}
Celery worker (_run_task):
  → job:{id} = running   + PUBLISH etl_status:{id}
  → run_fn() with stdout/stderr captured by _JobLogger
  → each print → PUBLISH etl_logs:{id} + append logs/{id}.log
  → save_logs → etl_logs:{id} (24h) + logs/{id}.log
  → job:{id} = success | error + PUBLISH etl_status:{id}
  → POST webhook_url (if given)
  → on error: the task re-raises so Celery marks it failed
```

Behaviours worth knowing (read from the code):
- On failure, `save_logs(job_id, traceback)` **overwrites** the job log with the traceback.
- `JobStore`, `RequestTracker` and event publishing swallow all exceptions: a missing job does not prove it failed.
- Forecast status is written twice: `run_rscript` rewrites the whole record (new `started`, no `message`), then `task_forecast` writes again. Forecast logs are written only at the end, so a WebSocket opened during the run gets `4004`.
- No timeout and no lock anywhere: a killed worker leaves `job:{id}` at `running` until the 24h TTL, and concurrent jobs write the same `input/` and `output/` files.
- WebSocket: `etl_log_history` → `job_status_update` / `etl_log_entry` → `etl_log_complete` → close. Code `4004` when no history exists, which can happen right after the 202.

Two endpoints are **not** part of this model: `/post_forecast` and `/update_key` run the script inline inside an `async def` handler. They block the event loop and redirect the process-wide `stdout`. `async def` handlers are only safe when they merely call a non-blocking `.delay()`.

## Configuration

- `core/config.py` (pydantic-settings). Default env file is `etlhub/.env` (`_PROJECT_ROOT` is `etlhub/`), or the file named by `ENV_FILE`. That file does not exist in the repo; the real `.env` is at the root. Three things read an env file: `Settings` (`etlhub/.env`), `forecast_runner.py` and `/api/config/reload` (root `.env`), and `load_dotenv()` in `etl/scripts/config.py` (relative to the cwd).
- `get_settings()` is `lru_cache`d and is first called at import of `core/celery_app.py`, before `etl/scripts/config.py` runs `load_dotenv()`. **Read from the code, not executed:** the `REDIS_*` values of the root `.env` are probably ignored unless exported or `ENV_FILE` is set; Redis then defaults to `localhost:6379/0`.
- **Dynamic config** (Redis hash `app:config:dynamic`: `DHIS_URL`, `DHIS_TOKEN`, `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`) is read by the forecast container **and** by `etl/scripts/config.py`, which gives `ConfigStore` priority for these keys plus `DRYRUN` and `LOG_LEVEL`. It is not forecast-only.
- Variable tables: `references/reference.md`.

## Authentication

DHIS2 (API token or OAuth2). `get_current_user` (`api/auth/dhis2_auth.py`) uses `HTTPBearer(auto_error=False)` and a 120 s module-level token cache. It is applied **per endpoint** on `/api/config/*` and on `/auth/me` only. Every other router, including every write endpoint, the tracking routes and the log WebSocket, is open. `JWT_SECRET` exists in `Settings` but is not used. `etlui` only uses token login: `POST /auth/validate-token`, then it stores the raw DHIS2 token in `localStorage` and sends `Authorization: Bearer` on every axios call (the log WebSocket sends nothing). The OAuth routes exist but the front never calls them. `GET /api/config/` returns `DHIS_TOKEN` in clear.

## Forecast pipeline

Docker image `mvevans89/pridec_forecast:0.1.0` (the OpenAPI text says `latest`), launched by `forecast_runner.run_rscript` from a Celery task, host network, `SYS_NICE`.

- `params` dict → `task_forecast`. `.env` merged with Redis overrides into a temp file `/tmp/forecast_{id}.env` that holds secrets while the container runs.
- Volumes `{HOST_PWD}/input:/app/input:ro`, `{HOST_PWD}/output:/app/output:rw`. `HOST_PWD` is read with `os.getenv` (not `Settings`) and must be a **host** path containing `.env`; a missing `.env` raises an unhandled `FileNotFoundError`.
- No timeout on `subprocess.run`. The worker needs access to the Docker socket.
- A `.output_sig` file is generated after a run. `DELETE /output/reset` only checks that it exists and is non-empty, then `rm -rf output/` (with a `sudo rm -rf` fallback). Treat it as no protection.

## Running and testing

Python 3.12 (`test-venv`; the system `python3` is 3.11). From the repo root unless noted:

```bash
redis-server                                   # creates dump.rdb in the cwd
python -m etlhub.run_celery                    # worker, from the repo root
cd etlhub && python -m run_server              # API on 8111
cd etlhub && ../test-venv/bin/python -m pytest tests -m "not integration"
```

- `.vscode/launch.json` and `GETTING_STARTED.md` mention port 8000; `run_server.py` uses 8111.
- `etlhub/pytest.ini` starts with `[tool:pytest]`, so pytest ignores it: always pass `tests` and `-m`.
- 31 tests are collected (29 pass, 1 known failing, 1 integration deselected). They live in `tests/api/` and `tests/infrastructure/`. `conftest.py` replaces `redis`, `redis.asyncio`, `pridec_gee`, `pivot_dhis_tools`, `earthengine_api` and `geopandas` with a global `MagicMock`. `ee`, the real Earth Engine module, is not mocked. A passing test says nothing about real Redis behaviour.
- Untested: `config_router`, `forecast_report_router`, `validation_router`, `/post_forecast`, `/update_key`, the WebSocket, `JobStore`, `RequestTracker`, `ConfigStore`, `forecast_runner`, and every Celery task except `task_forecast`.
- CI: `etlhub-unit-tests.yml` (push/PR on `etlhub/**`) and `etlhub-integration-tests.yml` (PR, needs `DHIS_URL` and `DHIS_TOKEN` secrets).
- No linter or formatter is configured.

## Adding a job type

Five synchronized changes, in this order: service method → `run_<name>` wrapper → `task_<name>` + registry entry → router endpoint (202) → tests. Real templates for each step are in `etlhub-practices/references/templates.md`; the checklist is in `etlhub-practices/references/checklists.md`. A forgotten registry entry fails at request time with `ValueError("Unknown task type")`.

Adding a tracking endpoint: DTO in `domain/schemas/tracking.py` → method in `tracking_service.py` → route in `tracking_router.py`.

Two endpoints read **query parameters only** (`/fetch_disease`, `/validate_inputs`) although `etlui` sends a JSON body to them; the body is silently ignored.