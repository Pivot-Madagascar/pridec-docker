# etlhub — reference tables

Re-check against the code before relying on a line number or a default.

## Endpoints

"Auth" = `get_current_user` applied. Everything marked "—" is **open**.

| Method | Path | Router | Execution | Auth |
|---|---|---|---|---|
| POST | `/import_gee`, `/import_pivot_com`, `/import_pivot_csb` | `ingest_router` | Celery, 202 | — |
| POST | `/fetch_climate`, `/fetch_disease`, `/fetch_geojson` | `ingest_router` | Celery, 202 | — |
| POST | `/validate_inputs` | `validation_router` | Celery, 202 | — |
| POST | `/build_analytics` | `analytics_router` | Celery, 202 | — |
| POST | `/post_forecast`, `/update_key` | `analytics_router` | **Inline, blocks the event loop** | — |
| POST | `/forecast/` | `forecast_router` | Celery → `docker run`, 202 | — |
| GET | `/forecast/status/{job_id}` | `forecast_router` | Redis → `logs/{job_id}.json` | — |
| GET | `/api/tracking/requests[/{id}]` | `tracking_router` | Read | — |
| GET | `/api/tracking/etl-logs/{job_id}` | `tracking_router` | Read. `{job_id, status, message, logs}`: status/message from `job:{id}` (24 h), logs from Redis or `logs/{id}.log`; 404 only when both are missing | — |
| WS | `/api/tracking/etl-logs/{job_id}` | `tracking_router` | Redis pub/sub stream | — |
| GET, PUT | `/api/config/`, PUT `/api/config/reload` | `config_router` | Redis. DHIS URL/token read-only (from the login) | **Session** |
| POST | `/auth/login` | `auth_router` | Sync. Body `{dhis2_url, username, password}` → DHIS2 calls, Redis, `etlhub_session` cookie. 400 URL not allowed, 401, 429, 502 DHIS2, 503 Redis | — |
| POST | `/auth/logout` | `auth_router` | Revokes the DHIS2 token, 204, clears the cookie | — |
| GET | `/auth/me` | `auth_router` | Redis | **Session** |
| GET | `/output/forecast_report.html[/exists]` | `forecast_report_router` | File | — |
| POST | `/input/files/{config\|external_data}` | `input_router` | Sync, multipart field `file` (≤ 10 MB) → replaces `input/config.json` or `input/external_data.csv`. 413 too big, 422 invalid JSON object / CSV without `orgUnit`,`period` / other name. The server writes `forecast_start` = the cycle into `config.json` | — |
| GET | `/input/files` | `input_router` | Sync. `{config, external_data}` → `{exists, size?, modified?}` | — |
| GET | `/input/files/config/preview` | `input_router` | Sync, content of `input/config.json`. 404 absent, 422 not a JSON object | — |
| GET | `/input/files/external_data/preview?limit=100` | `input_router` | Sync, `{columns, rows, total_rows, period_range, org_units}`: first `limit` (1–500) rows, summary over the whole file read line by line. 404 absent | — |
| DELETE | `/input/files/{config\|external_data}` | `input_router` | Sync, deletes the file in `input/`. 404 absent, 422 other name | — |
| GET | `/pipeline/checkpoints?cycle=YYYYMM` | `pipeline_router` | SQLite (Redis in test mode), default cycle = the current month. `{cycle, cycle_state, current_step, run, lock, dry_run, steps[{step, done, accessible, items[{item, status, job_id, updated_at, launchable}]}]}` | Session |
| POST | `/pipeline/runs` | `pipeline_router` | Body `{source, disease}`, `?confirm`. Opens the forecast run of a couple (one at a time), empties `input/` and `output/`. 201 run, 409, 422 unknown couple | Session |
| DELETE | `/pipeline/runs/current` | `pipeline_router` | Abandons the open run, its items → pending. `{abandoned: couple}` | Session |
| POST | `/pipeline/imports/approve` | `pipeline_router` | Body `{decision: approve\|reject}`. The `approve_imports` decision of step data_import, prerequisite of `build_analytics`. `{decision}` | Session |
| POST | `/pipeline/runs/current/approve` | `pipeline_router` | Body `{decision: approve\|reject}`. `{couple, decision}` | Session |
| PUT | `/pipeline/mode` | `pipeline_router` | Body `{dry_run}`, `?confirm`. Writes `DRYRUN` to the dynamic config; test mode keeps checkpoints in Redis (`pipeline:dry_run:db`) only; leaving it discards them (needs confirm when there are any). 409 while a job runs | Session |
| DELETE | `/pipeline/lock` | `pipeline_router` | Frees the job lock (killed worker; the lock never expires), its running checkpoint → `error`. `{released: job_id\|null}` | Session |
| POST | `/calc_orgunit_alerts` | `analytics_router` | **501**: no script implements it yet (item of the CSB runs). Target (2026-10-12): runs `pridec etl calc_orgUnit_alerts` | Session |
| DELETE | `/output/reset` | `forecast_report_router` | `rm -rf output/` | `.output_sig` exists (not real auth) |
| GET | `/` | `main.py` | 307 redirect to `/docs` | — |

Every launch (`/import_*`, `/fetch_*`, `/validate_inputs`, `/build_analytics`, `/post_forecast`, `/update_key`, `/forecast/`) and `POST`/`DELETE /input/files/{name}` go through the pipeline gate (`etlhub/docs/pipeline-checkpoints.md`): **409** `{message}` while another job runs, when a prerequisite is not in `success`, or for a forecast-run job (`/fetch_*`, `/validate_inputs`, `/forecast/`, `/post_forecast`, input files) without an open run. Undoing a `success` needs `?confirm=true`, otherwise **409** `{code: "confirmation_required", message, impact{item, step, current_step, reset_items, blocked_steps, kept_items}}` and nothing is written. All messages are in English.

Pipeline revision of 2026-10-12 (`etlhub/docs/pipeline-checkpoints.md` §8): applied, except `/calc_orgunit_alerts` (still 501), the test-mode scope (`DRYRUN` stays global; target: `import_gee` and `post_forecast` only) and the level check of `external_data` uploads (target: 422 on a mismatch).

Router prefixes (`main.py`): `ingest`, `analytics`, `validation`, `auth` have none; `forecast` `/forecast`; `tracking` `/api/tracking`; `forecast_report` `/output`; `input` `/input`; `config` `/api/config`. `auth_router` has no OpenAPI tag.

Known endpoint-level quirks:
- `/validate_inputs` takes file paths and `input_dir` from the caller and writes `config_valid.json`, `input_valid.json`, `polygon_valid.geojson` there.
- `webhook_url` on any job: the worker POSTs `{job_id, status, message, logs_url}` (relative `logs_url`, 10 s timeout, no signature) to any URL, errors ignored.

## Settings (`core/config.py`)

| Variable | Default | Usage |
|---|---|---|
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` / `REDIS_PASSWORD` | `localhost` / `6379` / `0` / `""` | Every Redis connection (`Settings.redis_url`, one client per process in `infrastructure/redis_client.py`) |
| `LOGS_DIR` | `logs` | Job and request logs |
| `DATA_DIR` | `.` | Root of `output/` and `.output_sig` |
| `HOST_PWD` | `.` | Host path for the forecast Docker volumes (read from `Settings.host_pwd`; must be exported in the worker's environment) |
| `TRACKED_ENDPOINTS` | `""` (all) | Path prefixes to record (`/api/tracking` is never recorded) |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origin and `Origin` check |
| `DHIS2_AUTH_TIMEOUT` | `10.0` | Login DHIS2 call timeout |
| `DHIS2_ALLOWED_HOSTS` | `""` (every login refused) | `host[:port]` the login may send credentials to |
| `COOKIE_SECURE` | `true` | `Secure` flag of the session cookie (false for local http only) |
| `ENV_FILE` | root `.env` | Env file path; `.env.debug` only for VS Code debugging |

Read by the ETL scripts (`etl/scripts/config.py`), not by `Settings`: `DHIS_URL`, `DHIS_TOKEN`, `DHIS_USER`, `DHIS_PWD`, `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`, `DRYRUN`, `LOG_LEVEL`, `PIVOT_URL`, `PIVOT_TOKEN`, `GEE_PROJECT`, `GEE_SERVICE_ACCOUNT`, `GEE_VARIABLES`. `ConfigStore` overrides take priority for `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`, `DRYRUN`, `LOG_LEVEL`. `DHIS_URL` / `DHIS_TOKEN` come from the login (`dhis2:credential`); `.env` is used only with `DHIS_ENV_FALLBACK=true` in the process environment (CLI).

`.env.example` lacks `LOGS_DIR`, `DATA_DIR`, `HOST_PWD`, `ENV_FILE`, and writes `dryRun` while the code reads `DRYRUN`.

## Redis

| Role | Keys / channels |
|---|---|
| Celery broker and backend | default queues, `redis://{host}:{port}/{db}` |
| Job state | `job:{id}` |
| Job logs | `etl_logs:{id}` (24 h TTL) |
| Pub/sub | `etl_logs:{id}`, `etl_status:{id}` |
| Dynamic config | hash `app:config:dynamic` |

One sync Redis client per process (`infrastructure/redis_client.py`) plus the async pool of the WebSocket. HTTP request logs live in SQLite `logs/etlhub.db` (30 days), not in Redis. File fallback for jobs: `logs/{id}.log`, `logs/{id}.json`.

## Celery (`core/celery_app.py`)

Explicit: `task_track_started=True`, JSON serializers, `accept_content=["json"]`. Everything else is the Celery default: `acks_late=False`, no time limits, no retries, `worker_prefetch_multiplier=4`, `result_expires` one day, concurrency = CPU count. `run_celery.py` passes only `--loglevel=info`.

## Exceptions → HTTP (`main.py`)

| Exception | Code |
|---|---|
| `JobNotFoundError` | 404 |
| `ValidationError` | 400 |
| `ETLException` | 500 |

`CeleryTaskLauncher.launch` raises a plain `ValueError` for an unknown task type, which is not one of the mapped exceptions.

## Docker (forecast)

Image `mvevans89/pridec_forecast:0.1.0`. Command `forecast --config_valid <path> --input_valid <path> --polygon_valid <path>`. Volumes `{HOST_PWD}/input:/app/input:ro` and `{HOST_PWD}/output:/app/output:rw`. Network `host`, capability `SYS_NICE`. Env: temp file merging `.env` and Redis overrides.

## Repo-level facts

- `compose.yaml` defines only `etl` and `forecast` (`etlui` and `web` are commented out). There is no etlhub Dockerfile and no Redis service, so deployment of etlhub is undocumented.
- `etl/requirements.txt` and `etlhub/requirements.txt` pin different versions of `pridec_gee` and `pivot_dhis_tools`.
- `etl/scripts/config.py` imports `etlhub`, but `etl/Dockerfile` copies only `scripts/` and `etl/requirements.txt` has no `redis`: whether the `etl` image still works is unconfirmed.