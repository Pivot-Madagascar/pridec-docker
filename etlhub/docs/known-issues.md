# etlhub — Known issues

Findings from a read-only inspection of the repository. Nothing here has been fixed. Items marked *unverified* come from reading the code only.

## 1. Security (highest risk first)

1. **Almost no authentication.** Only `/api/config/*` and `/auth/me` use `get_current_user`. Unprotected: every ETL POST, `/forecast/`, `/post_forecast`, `/update_key`, `/validate_inputs`, `DELETE /output/reset`, `GET /api/tracking/*` and the log WebSocket. Fix: `dependencies=[Depends(get_current_user)]` on each router except `auth_router`.
2. **`DELETE /output/reset`** (`api/routers/forecast_report_router.py`): the "signature" only checks that `.output_sig` exists and is non-empty. Falls back to `sudo rm -rf`.
3. **SSRF**: `/auth/validate-token` sends the token to any `dhis2_url` when `DHIS2_ALLOWED_HOSTS` is empty (the default). `webhook_url` lets the worker POST to any URL (`infrastructure/tasks.py`, host network).
4. **`/validate_inputs`** takes free file paths in the query and writes `config_valid.json`, `input_valid.json`, `polygon_valid.geojson` into a free `input_dir`.
5. **Forecast**: `ForecastParams` is passed as-is to `docker run`. A temp env file holds secrets for the whole run. No timeout.
6. **`GET /api/config/` returns `DHIS_TOKEN` in clear** (`ConfigResponse` has a `dhis_token` field). `etlui` puts it in a password input (`ConfigView.vue`), so it is hidden on screen but present in the DOM and the store.
7. **Middleware logs the full URL, query string included** (`middleware.py:77-86`), to `logs/requests/*.json` and `req:{id}`. A secret in a query string (a `webhook_url` carrying a token, the OAuth `code` of `/auth/dhis2/callback`) is stored. No bodies and no headers are logged, so the `Authorization` token is not. `X-Request-ID` is accepted from the client and used as a file name (`request_tracker.py:44`): possible path traversal (read, not tested).
8. **The log WebSocket and `/api/tracking/*` are open**, and `etlui` sends no token on the WebSocket (`useWebSocketLogger.ts:46-49`).
9. **OAuth is half-wired.** The callback validates the OAuth `access_token` with `Authorization: ApiToken …` (`dhis2_auth.py:59`); OAuth tokens normally use `Bearer` (cannot be verified without DHIS2). The `HTTPException(400)` at `router.py:112` is caught by the `except Exception` at `router.py:116-120`, and `code` is a query parameter on a POST. `etlui` never calls `/auth/dhis2/*` and has no `/login/callback` route, which is the default `DHIS2_REDIRECT_URI`.

## 2. Layering violations

| Violation | Where |
|---|---|
| application → api | `application/use_cases/etl_use_cases.py:40`, `validation_use_cases.py:30` (`etlhub.api.etl_events`) |
| infrastructure → api | `infrastructure/tasks.py:52,79`, `forecast_runner.py:172,177` |
| core → api | `core/dependencies.py:7` (unused import) |
| api → infrastructure without DI | `api/routers/config_router.py:9`, `api/middleware.py:12` |
| application → Redis (indirect) | `etl/scripts/config.py:3` imports `ConfigStore` |
| application → pandas/geopandas | `validation_use_cases.py:9-10` |

The `EventPublisher` port exists in `domain/interfaces/` but is never injected. Proposed fix: move `ETLEventManager` to `infrastructure/` and inject it.

## 3. Behaviour worth knowing

- `/post_forecast` and `/update_key` run synchronously in `async def` handlers (`analytics_service.py:22-47`).
- `JobStore`, `RequestTracker` and pub/sub publishing swallow every exception.
- ETL failure: `save_logs` overwrites the job log with the traceback (`tasks.py:75`, `job_store.py:59`).
- Forecast status is written and published twice (`forecast_runner.py:163-178` and `tasks.py:150,160`). `task_forecast` duplicates `_run_task` instead of using it.
- WebSocket (`api/websockets/etl_logs.py`): `pubsub.get_message()` defaults to `timeout=0.0`, so the `while True` loop busy-waits and the 30s `wait_for` never fires. If the job ends between the status read and `subscribe`, the client waits forever. Closes with `4004` if no history yet.
- `middleware.py:41`: `threading.local` shared across asyncio requests.
- `HOST_PWD` read via `os.getenv` in `forecast_runner.py:87` instead of `Settings.host_pwd`.
- `forecast_runner._build_dynamic_env_file` opens `.env` without checking it exists.
- *Unverified*: `Settings` reads `etlhub/.env`, which does not exist, and `load_dotenv()` in `etl/scripts/config.py` runs after the first cached `get_settings()`. The `REDIS_*` values of the root `.env` may therefore be ignored.

### More behaviour (from the architecture audit, read from the code)

- **Forecast logs are written only at the end** (`forecast_runner.py:165-168`): a WebSocket opened during the run always gets `4004`, and `etlui` does not retry because the close is clean (`useWebSocketLogger.ts:81-89`). For ETL jobs the same happens if the WebSocket opens before the first `print`.
- `run_rscript` rewrites the whole job record with a new `started` and no `message` (`forecast_runner.py:80-85`). The "started is kept" fix only holds for ETL tasks (`tasks.py:44`).
- **No timeout and no reconciliation.** No Celery time limit, no timeout on the forecast `subprocess.run`. A killed worker leaves `job:{id}` at `running` until the 24h TTL, and the WebSocket stays open. `/tmp/forecast_{id}.env` is removed in a `finally`, not after a SIGKILL.
- **No lock, no deduplication, no idempotence.** Two simultaneous `fetch_*`, `validate_inputs` or `forecast` runs write the same `input/` and `output/` files. Imports resend the same `dataValueSets` each time; deduplication depends on DHIS2.
- `build_analytics` ignores `DRYRUN`. Whether `update_key` really calls DHIS2 when `DRYRUN=true` depends on the installed `pivot_dhis_tools`, which is not in the repository (unverified).
- Scripts write under `os.getcwd()/input|output`. The API's cwd is the repo root (`main.py` `os.chdir`); the worker's cwd is unverified.
- `list_recent` globs every file in `logs/requests/`, calls `stat()` on each, sorts by modification time, and reads until `limit` matches: with a rare `endpoint` filter it can read them all. 511 files at the time of the audit. Redis is never used for the list.
- `JobStore` builds a Redis client per instance, so every task opens its own connection (`job_store.py:11-22`).
- The `ValidationError` and `TaskLaunchError` handlers exist (`main.py:36-43`) but nothing raises these exceptions today.
- `etlui` marks a step `success` as soon as it receives the 202 (`useEtlPipeline.ts:91,110,140,193`).

## 4. Dead code and duplication

- Dead: `JWT_SECRET`, `track_service` (middleware), `ValidationResponse`, `BaseSchema`, `get_request_tracker_repo`, `verify_signature` (`forecast_runner.py:63`), `get_etl_event_manager` import, `import uuid` in `validation_router.py`.
- Duplicated: `_get_output_dir` and signature check (`forecast_runner.py` and `forecast_report_router.py`), five separate Redis clients, ten near-identical Celery tasks, `__import__(...)` used to call `get_settings`.

## 5. Tests

- `etlhub/pytest.ini` uses `[tool:pytest]` (setup.cfg syntax): the whole file is ignored, which causes the `PytestUnknownMarkWarning` for `integration`. Fix: rename the header to `[pytest]`.
- `test_tracking_router.py:10,22,34` and `test_auth.py` patch names that have no effect (already imported). They pass thanks to `override_dependencies`.
- `conftest.py` does not mock `ee`.
- No linter, formatter or type checker configured.

## 6. Documentation and config drift

- `etlhub/docs/ARCHITECTURE.md` was rewritten on 2026-10-02. The old version said: 28 tests (there are 31); dynamic keys are forecast-only (false: `etl/scripts/config.py:7-15` reads them); `*.pyc` files are versioned (false: `git ls-files '*.pyc'` returns nothing, but `etlhub/hubcenter.egg-info/` is versioned despite `.gitignore:27`); `infrastructure/` is untested (a `task_forecast` test exists); about 2,600 lines (3,267 including tests).
- `GETTING_STARTED.md:73` says port 8000. `run_server.py` uses 8111.
- Two diverging versions of the skill: `etlhub/docs/SKILL.md` and `.claude/skills/etlhub/implementation.md`. A skill file must be named `SKILL.md` to be discovered, so `implementation.md` is probably not loaded.
- `.env.example`: lacks `LOGS_DIR`, `DATA_DIR`, `HOST_PWD`, `ENV_FILE`; writes `dryRun` while the code reads `DRYRUN`; has `GEE_PROJECT =` with a space. `.env` declares `DHIS_URL` twice.
- Version drift: `pridec_gee` and `pivot_dhis_tools` differ between `etlhub/requirements.txt` and `etl/requirements.txt`.
- The OpenAPI text of `/forecast/` says image `:latest`, the code uses `:0.1.0`.
- `compose.yaml` has no etlhub, no Redis. No etlhub Dockerfile. `hubcenter.egg-info/` has no source `setup.py`/`pyproject.toml`.

## 7. Open questions

- Does the rebuilt `mvevans89/pridec_etl` image still work? `etl/scripts/config.py:3` imports `etlhub`, but `etl/Dockerfile` only copies `scripts/` and `etl/requirements.txt` has no `redis`.
- Does `etlui` reconnect after a `4004` right after launching a job?
- Celery pool and concurrency in production (default prefork, no `--concurrency`)?
- How is etlhub deployed?
- Front/back mismatch on JSON bodies for `/fetch_disease` and `/validate_inputs`: fix the front or the back?
- Should the OAuth routes stay? The front never uses them.
- `DRYRUN` and `LOG_LEVEL` are read from Redis by the scripts but cannot be edited through `/api/config`. Intended?
- In which working directory does the worker run in practice, and with which Celery pool? This decides where `input/` and `output/` land.
- `README.md` mentions `compose-prod.yaml`, which is not in the repository. Is there a production setup elsewhere?
- The reasons for the architecture choices are not recorded in commits. `local-docs/` (not versioned) was not read.