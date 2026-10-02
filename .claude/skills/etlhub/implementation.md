---
name: etlhub
description: "Implementation guide for the ETLHub (Hub Center API) FastAPI service, which exposes the PRIDE-C ETL scripts (etl/scripts/*.py) and the R forecast pipeline via HTTP + Celery/Redis, with real-time WebSocket log streaming. Use systematically whenever you need to add an ETL endpoint or job type, modify a Celery task, extend the forecast pipeline, change job tracking (job_store, request_tracker), touch Redis-backed state, dynamic configuration, or DHIS2 authentication, or refactor the hexagonal layers (domain, application, infrastructure, api), even if the user does not explicitly mention ETLHub."
metadata:
  version: 1.0.0
---

# ETLHub — Implementation Guide

**FastAPI** service (port **8111**) that exposes the PRIDE-C ETL scripts (`etl/scripts/*.py`) and the R forecast pipeline via **Celery + Redis**. Consumed by the Vue front-end `etlui`.

## Layered Architecture

```
etlhub/
├── main.py                 # App composition, exception handlers, routers
├── core/                   # Cross-cutting: config, dependency injection, Celery
│   ├── config.py           #   Settings (pydantic-settings, .env)
│   ├── dependencies.py     #   Depends() providers
│   └── celery_app.py       #   Celery instance (broker/backend Redis)
├── domain/                 # Business core, no technical dependencies
│   ├── exceptions.py       #   ETLException, JobNotFoundError, ValidationError, TaskLaunchError
│   ├── interfaces/         #   Ports (Protocol): JobRepository, TaskLauncher, EventPublisher…
│   └── schemas/            #   Pydantic DTOs: ETLResponse, ForecastParams, JobStatus…
├── application/use_cases/  # Use cases
│   ├── *_service.py        #   Services (generate job_id, delegate to TaskLauncher)
│   ├── etl_use_cases.py    #   ETL script wrappers + stdout/stderr capture
│   └── validation_use_cases.py
├── infrastructure/         # Adapters (port implementations)
│   ├── tasks.py            #   Celery tasks, CeleryTaskLauncher, DefaultWebhookNotifier
│   ├── job_store.py        #   JobStore (Redis + log files)
│   ├── request_tracker.py  #   RequestTracker (Redis + logs/requests/*.json)
│   ├── config_store.py     #   ConfigStore (Redis hash)
│   └── forecast_runner.py  #   Docker run for R pipeline
├── api/                    # Inbound adapters
│   ├── routers/            #   REST endpoints
│   ├── websockets/         #   Log streaming
│   ├── auth/               #   DHIS2 authentication
│   ├── middleware.py       #   CORS + request tracking
│   └── etl_events.py       #   ETLEventManager (Redis pub/sub)
└── presentation/           # Static HTML landing page
```

### Dependency Rules

- `api` → `application`, `core`
- `application` → `domain`
- `infrastructure` → `domain`, `application`
- `domain` depends on **nothing**
- Dependency injection via `core/dependencies.py`: adapters are singletons (`@lru_cache`), services are built per-request via `Depends()`.

## Asynchronous Model (the one to follow)

### Job Lifecycle

```
UI → POST /import_gee?webhook_url=…
  → Router → Service.import_gee(webhook_url)
    → job_id = "import_gee_<8 hex>"
    → task_launcher.launch("import_gee", job_id, webhook_url=…)
  → Router → 202 {status: accepted, job_id}
UI → WS /api/tracking/etl-logs/{job_id}
Celery Worker:
  → SET job:{id} = running + PUBLISH etl_status:{id}
  → run_fn() with stdout/stderr capture → _JobLogger
  → each print → PUBLISH etl_logs:{id} + append logs/{id}.log
  → SETEX etl_logs:{id} (full logs)
  → SET job:{id} = success/error + PUBLISH etl_status:{id}
  → POST webhook_url (if provided)
```

### Job ID Format

`<type>_<uuid4[:8]>`, generated on the **service** side. Examples: `import_gee_a1b2c3d4`, `forecast_x7y8z9w0`.

### WebSocket Protocol

`etl_log_history` (history) → `job_status_update` / `etl_log_entry` (live) → `etl_log_complete` then close. Code `4004` if no history.

### Persistence

Redis (24h TTL) with file fallback (`logs/*.log`, `logs/*.json`, `logs/requests/*.json`).

## Broader Constraints

### Configuration

`core/config.py` (pydantic-settings, `.env` file pointed to by `ENV_FILE`, default `etlhub/.env`):

| Variable | Default | Usage |
|---|---|---|
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | `localhost` / `6379` / `0` | All Redis connections |
| `LOGS_DIR` | `logs` | Job and request logs |
| `DATA_DIR` | `.` | Root for `output/` and `.output_sig` |
| `HOST_PWD` | `.` | Host path for Docker forecast volumes |
| `TRACKED_ENDPOINTS` | `""` (all) | Middleware tracing prefixes |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origin |
| `DHIS2_CLIENT_ID` / `_SECRET` / `_REDIRECT_URI` | — | DHIS2 OAuth2 |
| `DHIS2_AUTH_TIMEOUT` | `3.0` | Auth call timeout |
| `DHIS2_ALLOWED_HOSTS` | `""` (all allowed) | DHIS2 URL whitelist |

The DHIS2 URL comes from `etl/scripts/config.get_dhis_url()`. Hot-editable keys (`DHIS_URL`, `DHIS_TOKEN`, `PARENT_OU`, `OU_LEVEL`, `DISEASE_CODE`) live in Redis hash `app:config:dynamic`; they only apply to the forecast container.

### Authentication

- **DHIS2**: API token or OAuth2 (`/auth/dhis2/login`, `/auth/dhis2/callback`)
- Only `/api/config/*` and `/auth/me` require `get_current_user` (to be extended to all routers)

### Exceptions

Domain exceptions are translated to HTTP in `main.py`:

| Exception | HTTP Code |
|---|---|
| `JobNotFoundError` | 404 |
| `ValidationError` | 400 |
| `TaskLaunchError` / `ETLException` | 500 |

## Development Recipes

### Adding a New ETL Job Type

Step-by-step, layer by layer:

1. **Domain** — If needed, add a DTO to `domain/schemas/` and/or a port to `domain/interfaces/`.

2. **Application / Service** — In the relevant service (e.g. `IngestionService`), add a method:
   ```python
   def new_task(self, webhook_url: str | None = None) -> str:
       job_id = f"new_task_{uuid.uuid4().hex[:8]}"
       self._task_launcher.launch("new_task", job_id, webhook_url=webhook_url)
       return job_id
   ```

3. **Application / Use Case** — In `etl_use_cases.py` (or `validation_use_cases.py`), add a wrapper:
   ```python
   def run_new_task(job_store=None, job_id=None) -> None:
       _execute_etl_job(new_task_fn, job_store=job_store, job_id=job_id, name="new_task")
   ```
   The `_execute_etl_job` pattern captures `stdout`/`stderr` via `capture_stdout(job_id)` and raises `ETLException` on error.

4. **Infrastructure / Task** — In `tasks.py`, add the Celery task:
   ```python
   @celery_app.task(bind=True)
   def task_new_task(self, job_id: str, webhook_url: str | None = None):
       _run_task(self, job_id, "Task description", run_new_task, webhook_url=webhook_url)
   ```
   Then register it in `CeleryTaskLauncher`:
   ```python
   self._registry = {
       ...
       "new_task": task_new_task,
   }
   ```

5. **API / Router** — In the relevant router (e.g. `ingest_router.py`), add the endpoint:
   ```python
   @router.post(
       "/new_task",
       response_model=ETLResponse,
       status_code=202,
       summary="Description",
       description=(
           "Launches the task in the background. "
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

6. **Main** — The router is already included via `app.include_router(...)` in `main.py` if it uses an existing router. Otherwise, add a new `APIRouter` and include it.

### Adding a Tracking Endpoint

1. Add a DTO to `domain/schemas/tracking.py` if needed.
2. Add a method to the tracking service (`tracking_service.py`).
3. Add the endpoint to `tracking_router.py`.

### Modifying the Forecast Pipeline

Forecast is special: it launches a Docker container (`mvevans89/pridec_forecast:0.1.0`) via `forecast_runner.run_rscript`.

- Parameters are passed in `params` (dict) to Celery task `task_forecast`
- `.env` is merged with Redis overrides (`ConfigStore`) into a temp file
- Volumes: `input/` (ro), `output/` (rw)
- Status written to `job_store` and `logs/{job_id}.json`
- A signature `.output_sig` is generated to authorize `DELETE /output/reset`

### Testing

Tests are in `tests/api/`. They **mock** Redis, GEE, and geopandas via `conftest.py`.

```bash
pytest tests/ -v
```

To test a new router:
1. Create `tests/api/test_new_router.py`
2. Mock dependencies with `app.dependency_overrides`
3. Verify `job_id` in the 202 response

## Existing Endpoints

| Method | Path | Router | Execution | Auth |
|---|---|---|---|---|
| POST | `/import_gee`, `/import_pivot_com`, `/import_pivot_csb` | `ingest_router` | Celery (202) | — |
| POST | `/fetch_climate`, `/fetch_disease`, `/fetch_geojson` | `ingest_router` | Celery (202) | — |
| POST | `/validate_inputs` | `validation_router` | Celery (202) | — |
| POST | `/build_analytics`, `/calc_csb_alerts` | `analytics_router` | Celery (202) | — |
| POST | `/post_forecast`, `/update_key` | `analytics_router` | **Sync** | — |
| POST | `/forecast/` | `forecast_router` | Celery → `docker run` (202) | — |
| GET | `/forecast/status/{job_id}` | `forecast_router` | Redis → `logs/{job_id}.json` | — |
| GET | `/api/tracking/requests[/{id}]` | `tracking_router` | Read | — |
| GET | `/api/tracking/etl-logs/{job_id}` | `tracking_router` | Read | — |
| WS | `/api/tracking/etl-logs/{job_id}` | `tracking_router` | Pub/sub stream | — |
| GET/PUT | `/api/config/`, PUT `/api/config/reload` | `config_router` | Redis | **DHIS2** |
| POST | `/auth/validate-token`, GET `/auth/dhis2/login`, POST `/auth/dhis2/callback` | `auth_router` | DHIS2 call | — |
| GET | `/auth/me` | `auth_router` | DHIS2 call | **DHIS2** |
| GET | `/output/forecast_report.html[/exists]` | `forecast_report_router` | File | — |
| DELETE | `/output/reset` | `forecast_report_router` | Delete `output/` | "signature" |
| GET | `/` | `main.py` | Static HTML | — |

## Patterns and Conventions

### Services (application layer)

- Generate `job_id`: `f"{task_type}_{uuid.uuid4().hex[:8]}"`
- Delegate launch to `TaskLauncher` (Protocol port)
- Never call Celery tasks or ETL scripts directly
- Never touch Redis, log files, or event publication

### Use Cases (ETL script wrappers)

- Always go through `_execute_etl_job(fn, job_store=…, job_id=…)`
- `capture_stdout(job_id)` redirects `sys.stdout`/`sys.stderr` to `_JobLogger`
- `_JobLogger` writes to memory, `logs/{job_id}.log`, and publishes to Redis with level inferred from text (INFO/ERROR/WARNING/DEBUG)
- Exception raised as `ETLException(f"{name} failed: {e}")`

### Celery Tasks (infrastructure)

- Use `_run_task(self, job_id, task_name, run_fn, webhook_url=…)` as the template
- `_update_task_status` merges with existing record (don't overwrite `started`, `logs`)
- `_send_webhook` sends JSON POST `{job_id, status, message, logs_url}`
- Task **must** raise exception after "error" status (so Celery marks it failed)

### Routers (api)

- `status_code=202` for async tasks
- `response_model=ETLResponse`
- Explicit `summary` and `description` for OpenAPI
- `Depends(get_XXX_service)` for injection
- Handler is `async def` but service is sync (Celery `.delay()` is non-blocking)

### Redis

- **Celery broker/backend**: default broker and backend
- **Statuses and logs**: `job:{id}`, `etl_logs:{id}` (24h TTL)
- **Pub/sub**: channels `etl_logs:{id}`, `etl_status:{id}`
- **Dynamic config**: hash `app:config:dynamic`

### Docker (forecast)

- Image: `mvevans89/pridec_forecast:0.1.0`
- Command: `forecast --config_valid <path> --input_valid <path> --polygon_valid <path>`
- Volumes: `{HOST_PWD}/input:/app/input:ro`, `{HOST_PWD}/output:/app/output:rw`
- Network: `host`
- Capability: `SYS_NICE`
- Env: merged temp file (`.env` + Redis overrides)