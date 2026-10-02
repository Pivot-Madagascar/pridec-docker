# etlhub

## Purpose

FastAPI service (port 8111) that exposes the PRIDE-C ETL scripts (`etl/scripts/*.py`) and the R forecast pipeline over HTTP. Long jobs run in Celery workers, state lives in Redis, logs are streamed over WebSocket. Consumed by the Vue front-end `etlui`.

## Module map

- `core/` — config, `dependencies.py` (composition root), `celery_app.py`
- `domain/` — exceptions, ports (`interfaces/`), Pydantic DTOs (`schemas/`)
- `application/use_cases/` — `*_service.py` (generate `job_id`, call `TaskLauncher`), `etl_use_cases.py`, `validation_use_cases.py`
- `infrastructure/` — `tasks.py` (Celery + `CeleryTaskLauncher`), `job_store.py`, `request_tracker.py`, `config_store.py`, `forecast_runner.py`
- `api/` — `routers/`, `websockets/etl_logs.py`, `auth/` (DHIS2), `middleware.py`, `etl_events.py`
- `tests/` — `api/` and `infrastructure/`

Siblings in the repo:
- `etl/scripts/` is **imported in-process** by etlhub, and `etl/scripts/config.py` imports `etlhub.infrastructure.config_store` back (two-way coupling).
- `forecast/` (R) runs through `docker run` from the worker. Files are exchanged through `input/` (ro) and `output/` (rw).
- `etlui/` consumes the REST API and the WebSocket (see contracts below).

## Rules

- **Never call real endpoints against a real DHIS2 or the host.** `/import_*`, `/build_analytics`, `/calc_csb_alerts`, `/post_forecast`, `/update_key` write to DHIS2. `/forecast/` runs `docker run`. `DELETE /output/reset` runs `rm -rf output/`. None of them is authenticated. Manual runs need `DRYRUN=true`. Tests use `app.dependency_overrides`, never a real Celery or Redis.
- **Never print or copy secrets.** `.env`, `.env.debug` and `.gee-private-key.json` exist locally. Mention variable names only.
- **The `etlui` contracts are frozen.** `ETLResponse` = `{status, message, job_id, webhook_url}`. `JobStatus` = `{status, job_id, started, completed, logs, message}`. `job_id` = `<task_type>_<uuid4 hex[:8]>`. WebSocket messages: `etl_log_history`, `job_status_update`, `etl_log_entry`, `etl_log_complete`, close code `4004`. Any change must be mirrored in `etlui/src/composables/useWebSocketLogger.ts` and `useEtlPipeline.ts` in the same change.
- **Layering target**: `api` → `application`, `core` · `application` → `domain` · `infrastructure` → `domain`, `application` · `domain` → nothing. Do not add new violations. Existing ones are known debt (`etlhub/docs/known-issues.md`): do not refactor them unless asked. Real violations to avoid: `application` or `infrastructure` importing `etlhub.api.*`, and `api` using `infrastructure` without injection. Tolerated in practice, pending the team's confirmation: `api` → `domain` DTOs, any layer → `core` settings, `core/dependencies.py` as composition root, `application` → `etl.scripts` wrappers.
- **Adding a job type = 4 synchronized changes**: service method (generates the `job_id`, calls `task_launcher.launch`), `@celery_app.task` in `tasks.py` using `_run_task`, entry in `CeleryTaskLauncher._registry`, router returning 202 with `ETLResponse`. Use case wrappers go through `_execute_etl_job`.
- **No new blocking work inside an `async def` handler.** Use Celery.
- **Do not move or rename `etl/scripts` modules**, and do not touch the `os.chdir` (in `main.py` only) or the `sys.path` changes (`main.py` and `validation_use_cases.py`). Worker and API depend on them, and scripts write under `os.getcwd()/input|output`.

## Gotchas

- A Celery task must **re-raise** after writing the "error" status, or Celery reports success.
- `_update_task_status` merges with the existing record. Do not overwrite `started` or `logs`.
- `/post_forecast` and `/update_key` are **synchronous**: they block the event loop and redirect the global `stdout`. All other launch endpoints go through Celery (202).
- Dynamic config (`app:config:dynamic`: `DHIS_URL`, `DHIS_TOKEN`, `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`) is read by the forecast container **and** by `etl/scripts/config.py` (also `DRYRUN`, `LOG_LEVEL`). The old `ARCHITECTURE.md` says otherwise: it is wrong.
- `JobStore`, `RequestTracker` and event publishing use `except Exception: pass`. A job missing from Redis does not mean it failed, and Redis being down leaves no trace.
- On an ETL failure, `save_logs` replaces the job log (file and Redis) with the traceback only.
- The WebSocket closes with `4004` when no log exists yet. For forecast, logs are written only at the end, so a WebSocket opened during the run always gets `4004` and `etlui` does not retry.
- `etlui` sends a JSON body to `/fetch_disease` and `/validate_inputs`, but the backend reads query parameters only. The body is silently ignored.
- Forecast: `HOST_PWD` is read with `os.getenv` (not `Settings`) and must be a **host** path containing `.env`. The worker needs the Docker socket. There is no timeout. A temp file `/tmp/forecast_{id}.env` holds secrets during the run. The image tag is `0.1.0` (the OpenAPI text says `latest`).
- No timeout and no lock anywhere. A killed worker leaves `job:{id}` at `running` until the 24h TTL. Two simultaneous jobs can write the same `input/` and `output/` files.
- `GET /api/config/` returns `DHIS_TOKEN` in clear, and the middleware logs full URLs: never put a secret in a query string.
- Redis job state expires after 24h. Older jobs only exist in `logs/`.
- Only `/api/config/*` and `/auth/me` require `get_current_user`. Do not assume other routers are protected.
- Ports: `run_server.py` uses **8111**. `.vscode/launch.json` and `GETTING_STARTED.md` say 8000.
- `JWT_SECRET` is defined but unused.

## Commands

Python 3.12 (use `test-venv`; the system `python3` is 3.11). Run from the repo root unless noted.

- Redis: `redis-server`
- Worker: `python -m etlhub.run_celery`
- API: `cd etlhub && python -m run_server`
- Tests: `cd etlhub && ../test-venv/bin/python -m pytest tests -m "not integration"` (31 tests)
- One file: `cd etlhub && ../test-venv/bin/python -m pytest tests/api/test_ingest_router.py`
- Linter / formatter: none configured. Do not invent one.

## Method for new code (proposed, see `etlhub/docs/DEVELOPMENT.md`)

- Behaviour and its test ship in the same commit. For a new endpoint, task, service or bug fix, write the failing test first. History shows this has not been the practice so far (0 of 22 source commits added a test first), so say what you did instead of claiming TDD.
- Assert behaviour, not only `status_code` (18 of 31 tests only check it).
- New or changed functions: at most 50 lines and 4 parameters, annotated, no `except … pass`, no `print(`.
- Coverage baseline 58 % (infrastructure 37 %): do not lower it for the files you touch.
- Running the tests writes about 119 files into `logs/requests/` (git-ignored), because Redis is mocked and `RequestTracker` falls back to files. Do not delete them without asking.

## Required checks

- `etlhub/pytest.ini` starts with `[tool:pytest]`, so pytest ignores it entirely. Always pass `tests` and `-m` explicitly.
- `conftest.py` replaces Redis, GEE and geopandas with a global `MagicMock`: a passing test says nothing about real Redis behaviour. `ee` (the real earthengine module) is not mocked.
- Patching `etlhub.core.config.get_settings` or `etlhub.core.dependencies.get_*` does not affect code that already imported the name. Use `app.dependency_overrides`.
- Run the tests before and after any change in this module.
- Untested areas: `config_router`, `forecast_report_router`, `validation_router`, `/post_forecast`, `/update_key`, the WebSocket, `JobStore`, `RequestTracker`, `ConfigStore`, `forecast_runner`, all Celery tasks except `task_forecast`. Add a test when you change one of them.
- Changed a contract or an endpoint signature: update `etlui` and the endpoint table in the docs.

## Where to look next

- `etlhub/docs/ARCHITECTURE.md` — compact architecture: runtime topology, state, data pipeline order, decisions
- `etlhub/docs/DEVELOPMENT.md` — measured test, architecture and clean-code state; proposed rules for new code
- `etlhub/docs/known-issues.md` — security findings, layering violations, dead code, doc errors
- `.claude/skills/etlhub/SKILL.md` — how etlhub is built: architecture, job lifecycle, endpoint and config tables, forecast pipeline
- `.claude/skills/etlhub-practices/SKILL.md` — how to change it well: templates, missing best practices as small migrations, checklists