# Missing practices as small migrations

Each section: **Problem** (with evidence) → **Target** → **Steps** → **Tests** → **Risks**. Do one migration per change. Re-run `grep -n` before editing: line numbers come from an earlier inspection.

Ready-to-apply order: m5, m6 → m3 → m4 → m2 → m1 → the rest. The first three make later changes verifiable.

---

## m1 — Authenticate the routers

**Problem.** Only `/api/config/*` and `/auth/me` use `get_current_user`. Every ETL POST, `/forecast/`, `/post_forecast`, `/update_key`, `/validate_inputs`, `DELETE /output/reset`, `GET /api/tracking/*` and the log WebSocket are open, and several write to DHIS2 or the host.

**Target.** All routers protected except `auth_router`. Tracking is protected per route.

**Why per route for tracking.** The tracking router also holds the WebSocket. `HTTPBearer` needs a `Request`, and FastAPI does not inject one in a WebSocket context, so a router-level dependency would break the WebSocket.

**Steps.**
1. In `main.py`, import `Depends` and `get_current_user` (from `etlhub.api.auth`).
2. Add `_protected = [Depends(get_current_user)]` and pass `dependencies=_protected` to `include_router` for `ingest`, `analytics`, `forecast`, `validation`, `forecast_report`, `config`. Leave `auth_router` as is.
3. In `tracking_router.py`, add `dependencies=[Depends(get_current_user)]` on the three GET routes. Leave the WebSocket route alone (decision pending: see SKILL.md).
4. In `tests/conftest.py::override_dependencies`, add `app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}`.
5. Tests that use `app` without `override_dependencies` (e.g. `test_forecast_launch_forwards_webhook_url`) must switch to `override_dependencies`.
6. The existing `dependencies=[Depends(get_current_user)]` in `config_router.py` become redundant but harmless (the dependency is cached per request). Remove them in a later cleanup.

**Tests.** For one protected route: no header → 401; override active → 202. One test per router is enough.

**Risks.** `etlui` must send `Authorization: Bearer <token>` on every call. Check `etlui/src/services/api.ts` before merging. Anything else that calls the API (cron, `curl`, other services) breaks. Ask the user first.

---

## m2 — Stop running ETL inline in `async def` handlers

**Problem.** `/post_forecast` and `/update_key` call `run_post_forecast` / `run_update_key` directly from `AnalyticsService` (`analytics_service.py`, lines ~22-47) inside an `async def` handler. This blocks the event loop for the whole DHIS2 call, and `redirect_stdout` changes `sys.stdout` for the whole process.

**Target.** Same 5-layer pattern as every other job: service returns a `job_id`, Celery runs it, the router returns 202.

**Steps.**
1. `tasks.py`: import `run_post_forecast`, `run_update_key`; add
   ```python
   @celery_app.task(bind=True)
   def task_post_forecast(self, job_id: str, webhook_url: str | None = None):
       _run_task(self, job_id, "forecast publication", run_post_forecast, webhook_url=webhook_url)

   @celery_app.task(bind=True)
   def task_update_key(self, job_id: str, webhook_url: str | None = None):
       _run_task(self, job_id, "PRIDE-C key update", run_update_key, webhook_url=webhook_url)
   ```
   and register `"post_forecast"` and `"update_key"` in `CeleryTaskLauncher._registry`.
2. `analytics_service.py`: make both methods return `str` (the job_id) via `self._task_launcher.launch(...)`. Drop the `run_*` import and the inline `ETLResponse`/`ETLException` handling. Keep the constructor signature unchanged so `dependencies.py` and `conftest.py` need no change (`job_repo` and `webhook_notifier` become unused).
3. `analytics_router.py`: add `status_code=202`, change the description from "synchronously" to "asynchronously", and return `ETLResponse(status="accepted", ..., job_id=job_id, webhook_url=webhook_url)`.

**Tests.** Add router tests for both endpoints (202, `accepted`, `job_id`). Add a task test with the in-memory store (template 8): success and failure, failure must re-raise.

**Risks.** This is a **contract change**: the response goes from 200 `success` to 202 `accepted`. `etlui` must follow progress through the WebSocket instead of treating the response as final. Update `etlui/src/composables/useEtlPipeline.ts` in the same change. If a caller relied on the synchronous result, it breaks.

---

## m3 — No silent failures, and real logging

**Problem.**
- `except Exception: pass` in `job_store.py` (4 places), `request_tracker.py` (3), `tasks.py` (3), `forecast_runner.py` (4), `_JobLogger.write`/`flush`, `_send_webhook`. When Redis or a file is unavailable, jobs become invisible with no trace.
- Logging: 8 `print(` (6 in `validation_use_cases.py:77-93`, 2 in `forecast_runner.py:151,161`), 20 `logger.` calls in only 4 modules, no logging config. `tasks.py`, `job_store.py`, `etl_use_cases.py` have no logger.

**Target.** Every module that can fail has `logger = logging.getLogger(__name__)`. A swallowed exception is logged with the job id and the operation, at `WARNING`. Do **not** change the control flow: a failure to persist must still not crash the job.

**Steps (job_store first, it is the highest value).**
```python
import logging
logger = logging.getLogger(__name__)
...
except Exception as e:
    logger.warning("JobStore.get(%s) failed: %s", job_id, e)
```
Same for `set`, `save_logs` (Redis and file separately), `get_logs`. Then `request_tracker.py`, `tasks.py`, `forecast_runner.py`.

Careful in two places:
- **`_JobLogger.write`** is installed as `sys.stdout`/`sys.stderr` during a job. A `logger.warning` called from inside it can write back to `sys.stderr`, i.e. to `_JobLogger.write` itself, and recurse. This depends on the handler: Python's last-resort handler (used when nothing is configured) looks up `sys.stderr` at emit time, so it would recurse; a `StreamHandler` created by `basicConfig` keeps the original stderr and would not. Reasoning from how `logging` works, not tested here. Leave `_JobLogger` swallowing for now, or test it with a `caplog`-style test before changing it.
- **`_send_webhook`**: log the failure (job id, host only, not the full URL, it may carry a token).

`print(` → `logger.info(` in `validation_use_cases.py` and `forecast_runner.py`. Inside `capture_stdout`, a `print` is captured into the job log and sent to the UI. A `logger.*` call goes to the logging handlers instead, which may or may not end up in the job log depending on the handler (see above), and `INFO` is dropped when no config sets the level. Decide per call: user-facing job output stays `print`, diagnostics become `logger`.

Before adding any logging config, check `etl/scripts/` for an existing `setup_logging()` (one agent report mentions it; the other found no logging config in etlhub). Run `grep -rn "setup_logging\|basicConfig\|dictConfig" etl etlhub` and find out whether it is already called when etlhub imports the scripts, and which `LOG_LEVEL` it reads. If it exists, reuse it from `run_server.py` and `run_celery.py` rather than adding a second configuration. If it does not, add a one-time `logging.basicConfig(level=..., format=...)` there, driven by `LOG_LEVEL`. Without any config, Python's last-resort handler still prints WARNING and above to stderr.

**Tests.** `caplog` test: make Redis raise in `JobStore.get`, assert a warning is logged and `None` is returned.

**Risks.** Low. Watch for log noise when Redis is down (one warning per call); acceptable.

Also a known behaviour to fix here or separately: on failure `_run_task` calls `save_logs(job_id, tb)`, which overwrites the whole job log with the traceback. Prefer appending the traceback to the existing logs.

---

## m4 — Validate `webhook_url` in one place

**Problem.** `webhook_url` is accepted from anyone and POSTed from the worker (host network) with no scheme or host check: SSRF. `_send_webhook` also swallows all errors. `/auth/validate-token` has the same issue when `DHIS2_ALLOWED_HOSTS` is empty.

**Target.** One validator, called at the single choke point, `CeleryTaskLauncher.launch`, so every job type is covered. A `ValidationError` raised there already becomes a 400 through the handler in `main.py`.

**Steps.**
1. New `etlhub/core/webhook.py`:
   ```python
   from urllib.parse import urlparse

   from etlhub.core.config import get_settings
   from etlhub.domain.exceptions import ValidationError


   def validate_webhook_url(url: str | None) -> str | None:
       if url is None:
           return None
       parsed = urlparse(url)
       if parsed.scheme != "https" or not parsed.hostname:
           raise ValidationError("webhook_url must be an absolute https URL")
       allowed = [h.strip().lower() for h in get_settings().webhook_allowed_hosts.split(",") if h.strip()]
       if allowed and parsed.hostname.lower() not in allowed:
           raise ValidationError("webhook_url host is not allowed")
       return url
   ```
2. `core/config.py`: add `webhook_allowed_hosts: str = ""`.
3. `tasks.py::CeleryTaskLauncher.launch`: call `validate_webhook_url(webhook_url)` before `fn.delay(...)`.
4. Add `WEBHOOK_ALLOWED_HOSTS` to `.env.example`.

**Tests.** Unit tests for the validator: `None`, `http://`, no host, allowed host, disallowed host, empty allow-list. Router tests are unaffected because they replace the launcher.

**Risks.** Existing callers using `http://` webhooks break. Empty allow-list behaviour is a pending decision. Redirects (`urllib` follows them) are not covered: revalidate in `_send_webhook` if the user wants that. **Coverage gap:** `/post_forecast` and `/update_key` do not go through `launch()` today (they call `self._webhook_notifier.send(...)` inline), so they bypass this validator until m2 is done. Do m2 first, or also validate in `DefaultWebhookNotifier.send`. **Check before relying on the 400:** confirm that `main.py` registers its handler for `etlhub.domain.exceptions.ValidationError` (not Pydantic's class of the same name). Today nothing raises `ValidationError` or `TaskLaunchError`, so that path has never been exercised: add a test for it.

---

## m5 — Make the test configuration real

**Problem.** `etlhub/pytest.ini` starts with `[tool:pytest]` (setup.cfg syntax). pytest ignores the whole file, so `testpaths`, `pythonpath`, `addopts` and the `integration` marker are not applied, and `PytestUnknownMarkWarning` appears.

**Steps.** Change line 1 to `[pytest]`. Verified on a copy: 31 tests collected before and after.

**Side effects.** `-v` becomes default (CI already passes it); `pythonpath = .` adds `etlhub/` to `sys.path`; the warning disappears.

Also in `conftest.py`: `sys.modules['earthengine_api']` is the pip package name, but `etl/scripts/import_gee.py` imports `ee` lazily inside the function. The mock does nothing. Tests pass only because the import is lazy. Mock `ee` if a test ever reaches that function.

---

## m6 — Fix the failing test and the token cache key

**Problem.** `tests/api/test_auth.py::test_validate_token_endpoint_with_custom_url_returns_user` fails with `assert 'user123' == 'user456'`. **Probable cause (read from the code, not yet confirmed):** `_token_cache` (module-global in `dhis2_auth.py`) is keyed by token only, TTL 120 s, and ignores `dhis2_url`, so a previous test that cached `valid-token` → `user123` leaks into this one. **Confirm first**: run the failing test alone. If it passes alone and fails after `test_valid_token_authenticates_user`, the cache is the cause, and it is then a real bug (two DHIS2 instances sharing entries), not only a test problem.

**Steps.**
1. Key the cache on `(dhis2_url, token)`.
2. Add an `autouse` fixture in `test_auth.py` (or `conftest.py`) that clears `_token_cache` before each test.

**Tests.** The failing test itself, plus one asserting that the same token on two URLs does not share a cache entry.

---

## m7 — Env file loading order (decision pending)

**Problem (read from the code, not executed).** `Settings` reads `etlhub/.env` by default (`_PROJECT_ROOT = Path(__file__).parent.parent`), which does not exist; the real file is at the repo root. The only `load_dotenv()` is in `etl/scripts/config.py`. In both `run_celery.py` and `run_server.py`, `core/celery_app.py` calls `get_settings()` at import, before `load_dotenv()` runs, and `@lru_cache` freezes the result. So `REDIS_*` from the root `.env` are ignored unless exported in the shell or `ENV_FILE` is set; Redis is `localhost:6379/0`.

**Options to present.** (a) document and require `ENV_FILE`; (b) point `_PROJECT_ROOT` at the repo root; (c) call `load_dotenv` before the first `get_settings()`. Do not pick one without asking.

**Also:** `.env.example` lacks `LOGS_DIR`, `DATA_DIR`, `HOST_PWD`, `ENV_FILE`, and writes `dryRun` while the code reads `DRYRUN`. `forecast_runner.py` reads `HOST_PWD` with `os.getenv` instead of `Settings.host_pwd`.

---

## m8 — Celery settings (decision pending)

**Today** (`core/celery_app.py`): only `task_track_started=True`, JSON serializers, `accept_content=["json"]`. Everything else is default: no time limit, no retry, `acks_late=False`, `worker_prefetch_multiplier=4`, `result_expires` 1 day, concurrency = CPU count.

**Proposals to discuss.**
- `worker_prefetch_multiplier=1`: tasks are long; prefetching 4 starves other jobs behind one slow task.
- `task_soft_time_limit` / `task_time_limit`: forecast has no timeout at all (`subprocess.run` too). Pick values with the user per task type.
- `result_expires`: results are also kept in Redis by `JobStore` (24 h TTL); align them.
- Do **not** enable `acks_late` or `autoretry_for` by default. The scripts write to DHIS2 and may not be idempotent: a re-run after a worker crash could duplicate writes.
- A killed worker leaves `job:{id}` at `running` until its 24h TTL and the WebSocket stays open: there is no reconciliation. Decide whether a stuck-job sweeper is wanted.
- There is no lock either: concurrent `fetch_*`, `validate_inputs` or `forecast` runs write the same files. A per-step lock in Redis (`SET NX` with an expiry) is the smallest option; do not add it without asking.

---

## m9 — Layering: inject `EventPublisher`

**Problem.** `domain/interfaces/event_publisher.py` exists but is never used. `tasks.py:52,79`, `forecast_runner.py:172,177`, `etl_use_cases.py:40`, `validation_use_cases.py:30` import `etlhub.api.etl_events` directly (inside `try`/`except pass` blocks).

**Target.** Move `ETLEventManager` to `infrastructure/`, implement `EventPublisher`, and inject it.

**Approach.** Do it in two steps: (1) move the class and leave a re-export in `api/etl_events.py` so nothing breaks; (2) switch callers to the port one module at a time. Only do this if the user asks: it touches the job pipeline and has little test coverage. Add tests for `_run_task` first.

---

## m10 — Front/back mismatch on JSON bodies (decision pending)

`etlui` sends a JSON body to `/fetch_disease` (`useEtlPipeline.ts:208-211`, `disease_code`, `ou_level`) and to `/validate_inputs` (`:137`, the forecast config). The backend reads only query parameters (`ingest_router.py` `api_fetch_disease`, `validation_router.py:24-33`), so the bodies are silently ignored and defaults apply. Ask whether the backend should accept a body (a Pydantic model; this is a contract change) or the front should stop sending it. Note that `/validate_inputs` takes free file paths and an `input_dir` from the caller: restrict them to `input/` if the body is accepted.

---

## m11 — WebSocket loop (verify before changing)

**Read from the code, not measured.** In `api/websockets/etl_logs.py`, `pubsub.get_message(ignore_subscribe_messages=True)` is called without `timeout=`; redis-py then returns immediately when nothing is queued, so the `while True` loop spins and `wait_for(..., 30.0)` never times out. Also, if a job finishes between the history/status read and `subscribe`, the client waits forever. And the server closes with `4004` when no history exists yet, which can happen right after the 202, before the first log line; `etlui` has no special handling for 4004 (reconnects only on unclean closes, up to 5 times). **For forecast it is systematic**: logs are written only at the end (`forecast_runner.py:165-168`), so a WebSocket opened during the run always gets 4004, and `etlui` does not retry because the close is clean (`useWebSocketLogger.ts:81-89`). Fixing it means either writing logs early in `run_rscript` or sending an empty `etl_log_history` instead of 4004, which is a contract decision.

**Steps.**
1. Reproduce with a fake pubsub first (a test that counts `get_message` calls over 1 s).
2. Pass an explicit `timeout` to `get_message` (for example `1.0`), keep the `asyncio.TimeoutError` branch.
3. Subscribe **before** reading history, then re-check the job status after subscribing.
4. Decide with the user what `4004` should mean right after launch (wait briefly, or send an empty `etl_log_history`) and whether `etlui` should retry on it.

**Risks.** The WebSocket is part of the frozen contract: message types and close codes must not change without updating `etlui`.