# etlhub

## Purpose

FastAPI service (port 8111) that exposes the PRIDE-C ETL scripts (`etl/scripts/*.py`) and the R forecast pipeline over HTTP. Long jobs run in Celery workers, state lives in Redis, logs are streamed over WebSocket. Consumed by the Vue front-end `etlui`.

## Module map

- `core/` — config, `dependencies.py` (composition root), `celery_app.py`
- `domain/` — exceptions, `pipeline.py`, ports (`interfaces/`: `JobRepository`, `TaskLauncher`, `PipelineGate`, `RequestTrackerProtocol`, `DefaultFileSource`, `EventPublisher`, `AuthStore`, `ConfigRepository`), Pydantic DTOs (`schemas/`)
- `application/use_cases/` — `*_service.py` (generate `job_id`, call `CeleryTaskLauncher`), `etl_use_cases.py` (`ETL_JOBS`, stdout capture, `notify_webhook`), `validation_use_cases.py`
- `infrastructure/` — `tasks.py` (`task_etl`, `task_forecast`, `CeleryTaskLauncher`), `job_store.py`, `request_tracker.py`, `config_store.py`, `auth_store.py`, `forecast_runner.py`, `etl_events.py` (live job events, Redis pub/sub)
- `api/` — `routers/`, `websockets/etl_logs.py`, `auth/` (DHIS2), `middleware.py`
- `tests/` — `api/` and `infrastructure/`

Siblings in the repo:
- `etl/scripts/` is **imported in-process** by etlhub, `etl/scripts/config.py` is the CLI version (env / `.env` only) and must never import `etlhub`; `etlhub/script_config.py` (imported by `etlhub/__init__.py`) replaces its `_get` / `_dhis2_credential` with Redis and the login.
- `forecast/` (R) runs through `docker run` from the worker. Files are exchanged through `input/` (ro) and `output/` (rw).
- `etlui/` consumes the REST API and the WebSocket (see contracts below).

## Rules

- **Never call real endpoints against a real DHIS2 or the host.** `/import_gee`, `/build_analytics`, `/post_forecast`, `/update_key` and `POST /pipeline/imports/approve` (approve) write to DHIS2 (`/import_pivot_*` only fetch from Pivot into `input/temp_fetch` since 2026-11-20; the approval posts the elements chosen: `docs/decision-design/pivot-approval/pivot-approval.md`). `/forecast/` runs `docker run`. `POST /pipeline/runs` empties `input/` and `output/`. They only need a session, which a logged-in user has. Manual runs: in test mode only (DRYRUN = TEST MODE: production writes). Tests use `app.dependency_overrides`, never a real Celery or Redis.
- **Never print or copy secrets.** `.env`, `.env.debug` and `.gee-private-key.json` exist locally. Mention variable names only.
- **The `etlui` contracts are frozen.** `ETLResponse` = `{status, message, job_id, webhook_url}`. `JobStatus` = `{status, job_id, started, completed, logs, message}`. `job_id` = `<task_type>_<uuid4 hex[:8]>`. WebSocket messages: `etl_log_history`, `job_status_update`, `etl_log_entry`, `etl_log_complete`, close code `4004`. Any change must be mirrored in `etlui/src/composables/useWebSocketLogger.ts` and `useEtlPipeline.ts` in the same change.
- **Respect the architecture below** (hexagonal). Do not mix the layers, even to shorten a diff: ponytail never removes a port or a layer.
- **Adding a Celery job type = 3 changes**: script function in `ETL_JOBS` (`etl_use_cases.py`; `task_etl`, `CeleryTaskLauncher` and `IngestionService.launch` then accept it), the job in `domain/pipeline.py`, one entry in the `ingest_router.py` table (or `add_launch_route`), which returns 202 with `ETLResponse`. Shared `confirm` query params live in `api/routers/__init__.py`.
- **No new blocking work inside an `async def` handler.** Use Celery.
- **Do not move or rename `etl/scripts` modules**, and do not touch the `os.chdir` (in `main.py` only) or the `sys.path` changes (`main.py`; the worker gets the repo root through `python -m`). Worker and API depend on them, and scripts write under `os.getcwd()/input|output`.

## Architecture (hexagonal, to respect)

Imports go inward only:

| Layer | May import (etlhub) | Holds |
|---|---|---|
| `domain/` | nothing | rules (`pipeline.py`), DTOs, exceptions, **ports** (`interfaces/`, `typing.Protocol`) |
| `application/` | `domain`, `core` settings | use cases; they talk to the outside **only through ports** |
| `infrastructure/` | `domain`, `application`, `core` | adapters (Redis, SQLite, Celery, Docker) implementing the ports |
| `api/` | `application`, `domain` DTOs, `core` | HTTP / WebSocket; gets services and adapters by injection |
| `core/dependencies.py` | everything | composition root: the only place that binds a port to its adapter |

- A use case annotates its collaborators with **ports**, never with an `infrastructure` class, not even under `TYPE_CHECKING`.
- `api` gets services and ports from the getters of `core/dependencies.py` (`Depends(get_…)` in a route signature; a direct call such as `get_auth_store()` in middleware, helpers and `get_current_user`); it never imports `etlhub.infrastructure`. An adapter may be a module whose functions implement the port (`auth_store`, `etl_events`).
- A new adapter method used by a use case or a router goes into its port in the same change. A new adapter gets a port when `application/` uses it.
- A port with a single adapter is normal (the second implementation is the test fake): never delete a port as dead code or "yagni".
- `tests/test_architecture.py` walks every import (lazy and `TYPE_CHECKING` ones included) and fails on a new crossing. Its `ALLOWED_DEBT` is empty since 2026-10-23: never add an entry, fix the code.
- Tolerated, pending the team's decision: `application` → `etl.scripts` and the libraries they need (the ETL wrappers; `validation_use_cases.py` reads the files with pandas/geopandas), `api` → `domain` DTOs, any layer → `core` settings. The test checks `etlhub` imports only.
- No type checker runs: nothing checks that an adapter or a test fake matches its port. Keep them in sync by hand.

## Gotchas

- **Cycle journal (since 2026-10-19)**: every write of `CheckpointStore` appends to `pipeline_events` through `_event`, in the same transaction. A new write method must call it too (one test per write method). The actor and `request_id` come from `core/request_context.py` (a per-request dict set by `RequestTrackingMiddleware`, `actor` set by `get_current_user`); outside a request (Celery worker) the actor is `worker`. Test-mode events live in the Redis blob only, kept when test mode is left. `request_log` lines flagged `journal` are never purged.
- **Cycle passes (since 2026-10-22)**: a pass is one run of a cycle (month); `checkpoints`, `forecast_runs` and `pipeline_events` carry its `pass_id` (table `passes`: active, paused, complete, abandoned; one active per mode). Every write goes to the active pass (`_current`); a launch starts one on the target month, after a complete pass only with `confirm=true`; a month with a paused pass refuses launches until it is resumed (`POST /pipeline/passes/{id}/resume`) or abandoned. A pass stays active until the user pauses, abandons or completes it: a calendar month change no longer pauses it (since 2026-11-20; leaving test mode did until 2026-11-19: the mode is now per user). A launch that starts a pass **carries over** the imports (and `approve_imports`) done in another pass of the cycle with the same `params` and `dry_run`, both kept in every import's `launched` event since 2026-10-26 (`carried_over` events; `cycle-passes.md` § 11). Migration 1 (`_migrate_to_passes`) converts a month-keyed store (cut after each `cycle_closed`). See `docs/decision-design/cycle-passes/cycle-passes.md`.
- **Schema migrations are run by hand only (since 2026-11-04)**: `python -m etlhub.migrate` (`--check` lists what is pending), API and workers stopped; it backs each db up next to `etlhub.db` first. `PRAGMA user_version` must equal `SCHEMA_VERSION` (`len(CheckpointStore.MIGRATIONS)`), for `etlhub.db` and the test blob: a db behind or ahead makes the API refuse to start and every pipeline call raise `SchemaVersionError`. A change to `_SCHEMA` ships with a new migration at the end of `MIGRATIONS` and its test on a db of the previous version; never edit a released one. No down-migrations: going back = restore the backup. See `docs/decision-design/db-migrations/db-migrations.md`.
- **Foreign keys (since 2026-11-18, schema version 2)**: `pass_id REFERENCES passes(id)` on `checkpoints`, `forecast_runs`, `pipeline_events`, `availability_checks`, enforced by `PRAGMA foreign_keys = ON` in both store transactions: insert the pass before its rows, never delete a referenced pass. `request_id`, `cycle` and `job_id` stay plain columns (why: `docs/decision-design/foreign-keys/foreign-keys.md`).
- A Celery task must **re-raise** after writing the "error" status, or Celery reports success.
- `_update_task_status` merges with the existing record. Do not overwrite `started` or `logs`.
- `/post_forecast` and `/update_key` are **synchronous but off the event loop** (sync `def`, FastAPI threadpool, since 2026-11-17): the request waits for the script, the rest of the API keeps answering. They still redirect the process-wide `stdout`/`stderr`, so prints of other API threads during the run land in their job's log. During a job the root logging handler writes into the job's `_JobLogger` (each script's `setup_logging()` runs `basicConfig(force=True)` under the redirect): code called from `_JobLogger.write` (`JobStore.append_logs`) must log through its own non-propagating logger, or a failure loops until `RecursionError`. All other launch endpoints go through Celery (202).
- `GET /import_availability` (since 2026-10-26) is **synchronous but off the event loop** (a sync `def`, FastAPI threadpool): it runs `availability_report()` of `application/use_cases/check_import_availability.py`, read only, with the session's DHIS2 token, and journals `availability_checked` (or `availability_reused`) in the shown pass (so it is tracked too). Each section (one import) is stored in `availability_checks` and reused by every user of the cycle until that import is launched again, its parameters change or 30 days pass (`?refresh=true` skips the reuse). Its periods, CSB ids and codes are copied from the three import scripts: keep them in sync. See `docs/decision-design/import-availability/import-availability.md`.
- **Configuration fixed by a pass (since 2026-11-20, schema version 3)**: when a pass starts (`POST /pipeline/passes`, or a launch with no pass active) it fixes `PASS_CONFIG` in `passes`: `gee_variables` (Home's choice over `pridec_gee.AVAILABLE_VARIABLES`; NULL = all), `dry_run` (the mode's, recorded only: see DRYRUN = TEST MODE below), `parent_ou`, `log_level` (Redis then) and `dhis_url` (the last login), journaled with `pass_started`. Nothing changes them after: a launch from a session on another DHIS2 is refused (409, `_check_config`); a Celery job gets its pass's config with its launch (`job_context.job_pass_config`), read by `script_config._get` for `PASS_KEYS` (outside a Celery job: the active pass's, `pass_config()`); `_dhis2_credential` refuses a credential of another DHIS2. `GEE_VARIABLES` is no editable key; `GET /api/config` lists the variables read only. Passes from before have NULLs and behave as before. See `docs/decision-design/pass-config/pass-config.md`.
- Editable config (`app:config:dynamic`, `config_store.EDITABLE_KEYS`: `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`, `LOG_LEVEL`, `PIVOT_URL` (since 2026-11-20, read by `fetch_pivot.pivot_url()`; `PIVOT_TOKEN` stays in the environment, never in Redis: `GET /api/config` returns `has_pivot_token` only)) is copied from etlhub's `.env` (`ENV_FILE`) at each API start (`PARENT_OU` and `LOG_LEVEL` then apply to the passes started after: a pass fixes its own) (`main.py` lifespan, overwriting; a key missing from `.env` is removed; the API refuses to start if Redis fails) and by `PUT /api/config/reload`; `PUT /api/config` edits them all (`DRYRUN` is no editable key since 2026-11-23: the mode decides it). Under etlhub the ETL scripts read these keys from Redis only (`etlhub/script_config.py`; absent = default, Redis error = job fails); the forecast container gets them through its env file. The CLI never reads Redis.
- **DRYRUN = TEST MODE (owner's rule of 2026-11-20, applied since 2026-11-23):** test mode ⇒ every job is a dry run, production ⇒ every job writes to DHIS2. Nothing else chooses it: no `dry_run` launch parameter or `POST /pipeline/passes` body field (a client sending one is ignored), no Home switch, no `DRYRUN` of `.env` (the CLI's only). It is the mode served: `CheckpointStore.default_dry_run()` journals it with each launch (`launched` `dry_run`), and the scripts read it through `script_config._get("DRYRUN")` = `current_test_mode()` (a Celery job runs in its launcher's mode; never `.env`). Nothing carries a `dry_run` to the job. Passes from before follow it too: the `dry_run` a pass stored is ignored, the API shows the mode's (`_passes`). `update_key` in test mode is refused (409: `pivot_dhis_tools` ignores its `dryRun`). Production now writes: never launch a production job against a real DHIS2 without approval.
- `JobStore`, `RequestTracker` and event publishing use `except Exception: pass`. A job missing from Redis does not mean it failed, and Redis being down leaves no trace.
- On a job failure, `_run_task` appends the traceback to the job log (file and Redis).
- The WebSocket closes with `4004` only for an unknown job; jobs are `pending` from the 202 on, so the socket stays open for them. Job logs (ETL and forecast) are appended as they are printed (`JobStore.append_logs`, Redis and `logs/{id}.log`), so the socket streams them live.
- `etlui` sends a JSON body to `/fetch_disease` and `/validate_inputs`, but the backend reads query parameters only. The body is silently ignored.
- Forecast: `HOST_PWD` is read from `Settings.host_pwd`: it must be exported in the worker's environment (the root `.env` loaded later by `load_dotenv()` is not seen) and must be a **host** path containing `.env`. A missing `.env` marks the job `error`. Forecast paths must be under `input/` (422 otherwise). The worker needs the Docker socket. There is no timeout, by decision. A temp file `/tmp/forecast_{id}.env` holds secrets during the run. The image tag is `0.1.0`.
- One job at a time, in cycle order: every launch, upload and input delete goes through the pipeline gate (`CheckpointStore`, SQLite `logs/etlhub.db`) and gets **409** otherwise. Three steps (`data_import`, `forecast`, `system_update`); the forecast step is 9 runs (source × disease), one open at a time (`POST /pipeline/runs`), and run jobs need it (409 otherwise). **Opening a run empties `input/` and `output/`** and writes `DISEASE_CODE` / `OU_LEVEL` into the dynamic config at each run job. A new job type must be added to `domain/pipeline.py` (`PIPELINE`, and `RUN_TASKS` if it belongs to a run), or `resolve_slot` raises. A step counts only if the previous one does (`progress()` is chained), and undoing a `success` needs `?confirm=true` (409 `confirmation_required` with `impact` otherwise); launch routes pass `confirm` down to the gate. API messages are in English. The cycle follows the calendar month unless chosen with `PUT /pipeline/cycle`; a month change leaves the active pass active on its month (since 2026-11-20). Test mode (since 2026-11-19 **per user**: `PUT /pipeline/mode` writes the caller's session, a session starts in test; the global `pipeline:test_mode` key is gone): passes live in Redis only (in-memory SQLite serialized in `pipeline:dry_run:db`), files in `test/input` and `test/output`; each mode keeps its own active pass, but a user leaving a mode whose pass is active must pause or abandon it (`leave_mode`: 409 `confirmation_required` with `impact.actions`, then body `pass_action`; journaled `cause: mode_change` with its reason). **One job lock for both modes**: the `pipeline_lock` row of `logs/etlhub.db`, attached as `shared` to every test-mode transaction (`BEGIN IMMEDIATE`, Redis lock first, never the other way); a job of the other mode shows as `job_id` null, task `a job of the other mode`. `POST /calc_orgunit_alerts` is a 501 (no script): CSB runs cannot complete. A killed worker keeps the lock until `DELETE /pipeline/lock` (it never expires; since 2026-11-17 it asks the workers first, `TaskLauncher.is_active`, Celery tasks are queued with `task_id=job_id`: a job that may still run gets 409 `confirmation_required` until `confirm=true`), and `job:{id}` at `running` until the 24h TTL. No timeout on the jobs themselves, nor on the calls of the `etl/` scripts, **by decision** (2026-11-17: durations are never static, a forecast can exceed 10 min): never add one. Tests get the real gate on a temp db (`checkpoint_store` fixture) or `OpenGate`.
- The middleware logs full URLs, only `webhook_url` is masked (`api/middleware.py`, `_logged_url`): never put a secret in another query parameter, or mask it there. (`GET /api/config/` returns `has_dhis_token`, never the token.)
- **Mode per user and isolation (since 2026-11-19)**: the mode served is `core/job_context.current_test_mode()`: the session's (set by `get_current_user`, async, so the ContextVar reaches the route), or the job's (Celery kwargs `test_mode`, set by `_run_task`); test outside both. Every mode read of the store goes through its `test_mode` callable; every path through `work_dir` (`./input`, `./output` in production, `test/input`, `test/output` in test). What happens in one mode is never readable in the other: `cycles()`, `journal()`, the requests (`mode` of the session in the request's JSON; none: listed nowhere), job logs and their WebSocket (`has_job`). The three `fetch_*` scripts of `etl/` write `./input` whatever the mode: in test mode `etl_use_cases._into_mode_folder` sets production's file aside and moves theirs to `test/input` (safe because one job at a time). Tests: the autouse `production_mode` fixture and the async `app` user override serve production. See `docs/decision-design/mode-isolation/mode-isolation.md`.
- Tests: never `from tests.conftest import …` at module level or in a fixture of a new file: it re-runs conftest under a second name and replaces the `redis` mock, so `except redis.RedisError` stops matching in later tests (`test_auth.py`). Copy the small fake instead.
- Redis job state expires after 24h. Older jobs only exist in `logs/`.
- Every router except `/auth/login` and `/auth/logout` requires the session (`main.py`, `_session`). No roles (removed 2026-11-17): every logged-in user may call every route, `DELETE /pipeline/lock` and the journal CSV included. Do not add an admin check without asking.
- A run's `forecast_report.html` is copied to `uploads/<cycle>/<pass>/report_<source>_<disease>.html` (`uploads/dry_run/…` in test mode) when its `post_forecast` succeeds, because the next run empties `output/`. `GET /pipeline/runs/{source}/{disease}/report` serves it.
- Ports: `run_server.py` uses **8111**. `.vscode/launch.json` and `GETTING_STARTED.md` say 8000.
- `JWT_SECRET` is defined but unused.

## Commands

Python 3.12 (use `test-venv`; the system `python3` is 3.11). Run from the repo root unless noted.

- Redis: `redis-server`
- Worker: `python -m etlhub.run_celery`
- Schema migrations (by hand, API and workers stopped): `python -m etlhub.migrate --check`, then `python -m etlhub.migrate`
- API: `cd etlhub && python -m run_server`
- Tests: `cd etlhub && ../test-venv/bin/python -m pytest tests -m "not integration"` (351 tests; bare `pytest` works too since `pytest.ini` is read)
- One file: `cd etlhub && ../test-venv/bin/python -m pytest tests/api/test_ingest_router.py`
- Linter / formatter: none configured. Do not invent one.

## Method for new code (proposed, see `etlhub/docs/DEVELOPMENT.md`)

- Work with the **ponytail** skill (root `CLAUDE.md`): reuse what `etlhub` already has (registries, `add_launch_route`, `CheckpointStore`) before writing anything new; mark deliberate shortcuts with `ponytail:`.
- Behaviour and its test ship in the same commit. For a new endpoint, task, service or bug fix, write the failing test first. History shows this has not been the practice so far (0 of 22 source commits added a test first), so say what you did instead of claiming TDD.
- Assert behaviour, not only `status_code` (18 of 31 tests only check it).
- New or changed functions: at most 50 lines and 4 parameters, annotated, no `except … pass`, no `print(`.
- Coverage baseline 58 % (infrastructure 37 %): do not lower it for the files you touch.
- Running the tests writes about 119 files into `logs/requests/` (git-ignored), because Redis is mocked and `RequestTracker` falls back to files. Do not delete them without asking.

## Required checks

- `conftest.py` replaces Redis, GEE and geopandas with a global `MagicMock`: a passing test says nothing about real Redis behaviour. `ee` (the real earthengine module) is not mocked.
- Patching `etlhub.core.config.get_settings` or `etlhub.core.dependencies.get_*` does not affect code that already imported the name. Use `app.dependency_overrides`. `get_checkpoint_store` and `get_request_tracker` are `lru_cache` singletons: tests fill them with `use_instance` (`tests/conftest.py`).
- Run the tests before and after any change in this module.
- Untested areas: `config_router`, `forecast_report_router`, `validation_router`, `/post_forecast`, `/update_key`, the WebSocket, `JobStore`, `RequestTracker`, `ConfigStore`, `forecast_runner`, all Celery tasks except `task_forecast`. Add a test when you change one of them.
- Changed a contract or an endpoint signature: update `etlui` and the endpoint table in the docs.
- OpenAPI: every operation needs a `description` and declares its error codes; shared ones (`NOT_AUTHENTICATED`, `BLOCKED` for 409, `error_doc`) live in `api/routers/__init__.py`. The session cookie is marked in the schema from the real `get_current_user` dependency (`main.py`, `_openapi`). `test_route_protection.py` checks both.

## Where to look next

- `etlhub/docs/ARCHITECTURE.md` — compact architecture: runtime topology, state, data pipeline order, decisions
- `etlhub/docs/DEVELOPMENT.md` — measured test, architecture and clean-code state; proposed rules for new code
- `etlhub/docs/known-issues.md` — security findings, layering violations, dead code, doc errors
- `etlhub/docs/testing-QA/` — manual test logs: incidents (cause, fix) and testers' notes
- `etlhub/docs/decision-design/<feature>/` — design and decision docs per feature, implemented or under discussion (`pipeline-checkpoints/`, `pipeline-config/`, `default-input-files/`, `cycle-journal/`, `cycle-passes/`, `import-availability/`, `db-migrations/`, `mode-isolation/`, `pass-config/`, `pivot-approval/`)
- `.claude/skills/etlhub/SKILL.md` — how etlhub is built: architecture, job lifecycle, endpoint and config tables, forecast pipeline
- `.claude/skills/etlhub-practices/SKILL.md` — how to change it well: templates, missing best practices as small migrations, checklists