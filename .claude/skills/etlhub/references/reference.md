# etlhub — reference tables

Re-check against the code before relying on a line number or a default.

## Endpoints

"Auth" = `get_current_user` applied. Everything marked "—" is **open**.

| Method | Path | Router | Execution | Auth |
|---|---|---|---|---|
| POST | `/import_gee`, `/import_pivot_com`, `/import_pivot_csb` | `ingest_router` | Celery, 202 | — |
| POST | `/fetch_climate`, `/fetch_disease`, `/fetch_geojson` | `ingest_router` | Celery, 202 | — |
| POST | `/validate_inputs` | `validation_router` | Celery, 202 | — |
| POST | `/build_analytics`, `/calc_csb_alerts` | `analytics_router` | Celery, 202 | — |
| POST | `/post_forecast`, `/update_key` | `analytics_router` | **Inline, blocks the event loop** | — |
| POST | `/forecast/` | `forecast_router` | Celery → `docker run`, 202 | — |
| GET | `/forecast/status/{job_id}` | `forecast_router` | Redis → `logs/{job_id}.json` | — |
| GET | `/api/tracking/requests[/{id}]` | `tracking_router` | Read | — |
| GET | `/api/tracking/etl-logs/{job_id}` | `tracking_router` | Read | — |
| WS | `/api/tracking/etl-logs/{job_id}` | `tracking_router` | Redis pub/sub stream | — |
| GET, PUT | `/api/config/`, PUT `/api/config/reload` | `config_router` | Redis | **DHIS2** |
| POST | `/auth/validate-token` | `auth_router` | DHIS2 call | — |
| GET | `/auth/dhis2/login` | `auth_router` | DHIS2 | — |
| POST | `/auth/dhis2/callback` | `auth_router` | DHIS2 | — |
| GET | `/auth/me` | `auth_router` | DHIS2 call | **DHIS2** |
| GET | `/output/forecast_report.html[/exists]` | `forecast_report_router` | File | — |
| DELETE | `/output/reset` | `forecast_report_router` | `rm -rf output/` | `.output_sig` exists (not real auth) |
| GET | `/` | `main.py` | Static HTML | — |

Router prefixes (`main.py`): `ingest`, `analytics`, `validation`, `auth` have none; `forecast` `/forecast`; `tracking` `/api/tracking`; `forecast_report` `/output`; `config` `/api/config`. `auth_router` has no OpenAPI tag.

Known endpoint-level quirks:
- `/validate_inputs` takes file paths and `input_dir` from the caller and writes `config_valid.json`, `input_valid.json`, `polygon_valid.geojson` there.
- `/auth/validate-token` sends the token to any `dhis2_url` when `DHIS2_ALLOWED_HOSTS` is empty (the default).
- `webhook_url` on any job: the worker POSTs `{job_id, status, message, logs_url}` (relative `logs_url`, 10 s timeout, no signature) to any URL, errors ignored.

## Settings (`core/config.py`)

| Variable | Default | Usage |
|---|---|---|
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | `localhost` / `6379` / `0` | Every Redis connection |
| `LOGS_DIR` | `logs` | Job and request logs |
| `DATA_DIR` | `.` | Root of `output/` and `.output_sig` |
| `HOST_PWD` | `.` | Host path for the forecast Docker volumes (read with `os.getenv` in `forecast_runner.py`) |
| `TRACKED_ENDPOINTS` | `""` (all) | Middleware tracing prefixes |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origin |
| `DHIS2_CLIENT_ID` / `_SECRET` / `_REDIRECT_URI` | — | DHIS2 OAuth2 |
| `DHIS2_AUTH_TIMEOUT` | `3.0` | Auth call timeout |
| `DHIS2_ALLOWED_HOSTS` | `""` (all allowed) | DHIS2 URL whitelist |
| `JWT_SECRET` | — | Defined, **unused** |
| `ENV_FILE` | `etlhub/.env` | Env file path (that default file does not exist) |

Read by the ETL scripts (`etl/scripts/config.py`), not by `Settings`: `DHIS_URL`, `DHIS_TOKEN`, `DHIS_USER`, `DHIS_PWD`, `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`, `DRYRUN`, `LOG_LEVEL`, `PIVOT_URL`, `PIVOT_TOKEN`, `GEE_PROJECT`, `GEE_SERVICE_ACCOUNT`, `GEE_VARIABLES`. `ConfigStore` overrides take priority for `DHIS_URL`, `DHIS_TOKEN`, `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`, `DRYRUN`, `LOG_LEVEL`.

`.env.example` lacks `LOGS_DIR`, `DATA_DIR`, `HOST_PWD`, `ENV_FILE`, and writes `dryRun` while the code reads `DRYRUN`.

## Redis

| Role | Keys / channels |
|---|---|
| Celery broker and backend | default queues, `redis://{host}:{port}/{db}` |
| Job state | `job:{id}` |
| Job logs | `etl_logs:{id}` (24 h TTL) |
| Requests | `req:{id}` |
| Pub/sub | `etl_logs:{id}`, `etl_status:{id}` |
| Dynamic config | hash `app:config:dynamic` |

Five separate Redis clients are built (`JobStore`, `RequestTracker`, `ConfigStore`, `ETLEventManager`, the WebSocket pool). File fallback: `logs/{id}.log`, `logs/{id}.json`, `logs/requests/*.json`.

## Celery (`core/celery_app.py`)

Explicit: `task_track_started=True`, JSON serializers, `accept_content=["json"]`. Everything else is the Celery default: `acks_late=False`, no time limits, no retries, `worker_prefetch_multiplier=4`, `result_expires` one day, concurrency = CPU count. `run_celery.py` passes only `--loglevel=info`.

## Exceptions → HTTP (`main.py`)

| Exception | Code |
|---|---|
| `JobNotFoundError` | 404 |
| `ValidationError` | 400 |
| `TaskLaunchError`, `ETLException` | 500 |

`CeleryTaskLauncher.launch` raises a plain `ValueError` for an unknown task type, which is not one of the mapped exceptions.

## Docker (forecast)

Image `mvevans89/pridec_forecast:0.1.0`. Command `forecast --config_valid <path> --input_valid <path> --polygon_valid <path>`. Volumes `{HOST_PWD}/input:/app/input:ro` and `{HOST_PWD}/output:/app/output:rw`. Network `host`, capability `SYS_NICE`. Env: temp file merging `.env` and Redis overrides.

## Repo-level facts

- `compose.yaml` defines only `etl` and `forecast` (`etlui` and `web` are commented out). There is no etlhub Dockerfile and no Redis service, so deployment of etlhub is undocumented.
- `etl/requirements.txt` and `etlhub/requirements.txt` pin different versions of `pridec_gee` and `pivot_dhis_tools`.
- `etl/scripts/config.py` imports `etlhub`, but `etl/Dockerfile` copies only `scripts/` and `etl/requirements.txt` has no `redis`: whether the `etl` image still works is unconfirmed.