# etlhub — Known issues

Checked against the code on 2026-11-17 (commit `a720737`); first written on 2026-10-08, after the DHIS2 login and route protection work (commit `9f66b09`). Items marked *unverified* come from reading the code only. Fixed items are listed at the end of each section so the history stays readable.

Scope: etlhub only. Errors of the R forecast pipeline itself (the `pridec_forecast` image, INLA, the `PRIDEC` package) are not listed here; see the tickets in `testing-QA/` (e.g. `ticket-forecast-inla-com-malaria.md`).

Priority scale: **P1** fix next (security or a broken feature), **P2** fix soon (wrong behaviour, data integrity), **P3** when convenient.

## 0. Priorities at a glance

| Priority | Issue | Section |
|---|---|---|
| P2 | Pipeline revision: `calc_orgunit_alerts` still missing (no script in `etl/`, `skip_alerts` meanwhile) | 3 |
| P3 | Everything else below | — |

## 1. Security

1. *Removed (2026-10-23):* `DELETE /output/reset` and its `.output_sig` "signature" (no caller in etlui; opening a run empties `output/`). Forecast containers run as the worker's user (`forecast_runner._container_user`) and `output/` is created by the worker before `docker run`. Files left root-owned by older runs must be handed back once (`GETTING_STARTED.md`, "output/ owned by root").
2. *Fixed (2026-10-16):* SSRF through `webhook_url`. Every route takes the `WebhookUrl` type (`api/routers/__init__.py`): https to a host of `WEBHOOK_ALLOWED_HOSTS` only, 422 otherwise; empty list = every webhook refused. `notify_webhook` uses httpx, which does not follow redirects. *Unverified:* a DNS name of the allow-list that resolves to an internal address is still called.
3. *Fixed (2026-10-16):* `/validate_inputs` free paths. Its paths and `input_dir` take the `InputPath` type shared with `ForecastParams` (file path under `input/`, no `..`, no leading `-`), and the use case resolves them against the repo root instead of the worker's cwd.
4. *Fixed (2026-11-17):* a login or a logout while a job holds the pipeline lock no longer revokes the DHIS2 token that job read at its start (`api/auth/router.py`, `_job_running`); the token is only dropped from Redis and expires on its own (24 h at most), so etlhub may leave a few valid tokens it no longer knows. Still possible: a job still running when its token reaches its 24 h expiry gets 401 from DHIS2 (no timeout on jobs, by decision).
5. *Removed (2026-11-17):* roles. No admin check anywhere (`require_admin`, `is_admin`, `ADMIN_ONLY` deleted, etlui shows the Journal's CSV export and Job lock zone to everyone): every logged-in user of a host in `DHIS2_ALLOWED_HOSTS` may call every route, and the last one to log in is the DHIS2 identity of every job. Decided, not an issue.
6. *Fixed (2026-11-17):* request logs (SQLite `logs/etlhub.db`, 30 days) store the URL with the value of `webhook_url` masked (`api/middleware.py`, `_logged_url`: `webhook_url=[redacted]`, the other query parameters are kept for the tracking page and the journal). Bodies and headers are not logged, so the login password and cookies are not. A new free-text query parameter that can carry a secret must be masked there too.
7. *Fixed (2026-10-08):* a client `X-Request-ID` is kept only if it is a UUID (`api/middleware.py`, `_request_id`), so it can no longer overwrite another entry.
8. **P3 — The DHIS2 token is in clear in Redis** (`dhis2:credential`) and in its AOF/RDB files. Accepted: `redis.conf` binds to localhost, requires a password, and the data directory must stay `chmod 700`. The token lives 24 h and is revoked at logout.
9. **P3 — Public pages to decide**: `GET /`, `/docs`, `/redoc`, `/openapi.json` (the full API map).
10. **P3 — Forecast temp env file** `/tmp/forecast_{id}.env` holds the other `.env` secrets (`PIVOT_TOKEN`, GEE…) for the whole run and survives a SIGKILL. It no longer contains `DHIS_URL` / `DHIS_TOKEN`.

Fixed (2026-10-08): every router except `auth_router` requires the session, the log WebSocket included (origin check, close `4401`), guarded by `tests/api/test_route_protection.py` · `GET /api/config/` no longer returns the DHIS2 token · OAuth routes, `/auth/validate-token` and `JWT_SECRET` removed · login sends credentials only to `DHIS2_ALLOWED_HOSTS` · failed login after revoking the previous token no longer leaves it active in Redis.

## 2. Layering violations

None between etlhub layers since 2026-10-23, guarded by `tests/test_architecture.py` (`ALLOWED_DEBT` empty; rules in `CLAUDE.MD`, "Architecture").

*Fixed (2026-10-23):* `application` and `infrastructure` → `api.etl_events` (moved to `infrastructure/etl_events.py` behind the `EventPublisher` port, injected into `run_etl_job` and `AnalyticsService`) · `api` → `infrastructure` without injection in `middleware.py`, `auth/dhis2_auth.py`, `auth/router.py`, `routers/config_router.py`, `etl_events.py` (they go through `core/dependencies.py`: `get_request_tracker_repo`, `get_auth_store`, `get_config_store`; ports `AuthStore`, `ConfigRepository`) · `etl/scripts/config.py` no longer imports etlhub (2026-10-22).

Tolerated, not fixed (team decision pending, `CLAUDE.MD`): `application` → `etl.scripts` and pandas/geopandas (`validation_use_cases.py` reads the input files) (`infrastructure/checkpoint_store.py` → `etl.scripts.config.get_dry_run`: gone since 2026-11-23, DRYRUN = TEST MODE). Bypasses inside `infrastructure` (allowed by the rule): `tasks.py` builds `JobStore()` and calls `get_checkpoint_store()` directly.

## 3. Behaviour worth knowing

- *Fixed (2026-10-08):* the log WebSocket no longer busy-waits (1 s `get_message` timeout, 0.3 % CPU measured while waiting), subscribes before reading history, re-checks the job status every 10 s, stops when the client leaves, and closes with `4004` only for an unknown job. Jobs are recorded `pending` at launch. The tracking page follows pending/running jobs live in its request detail modal.
- *Fixed (2026-11-17):* `/post_forecast` and `/update_key` no longer freeze the API. Their handlers (`api/routers/etl/analytics_router.py`) are plain `def`, so FastAPI runs the synchronous service in its threadpool (the request still waits for the script; `request_context` follows, anyio copies the context). Guarded by `tests/api/test_analytics_router.py::test_inline_scripts_run_off_the_event_loop`.
- **P3 — Inline jobs redirect the process-wide `stdout`/`stderr`** (`etl_use_cases._execute_etl_job`). Since the handlers left the event loop, other API threads keep running during `update_key` (and the imports approval; `post_forecast` is a Celery job since 2026-11-24), and their prints and warnings land in that job's log. No data loss (the gate allows one inline job at a time, so the redirections never interleave). Upgrade: run both through Celery (202), a contract change for etlui (`.claude/skills/etlhub-practices/references/migrations.md`, m2).
- **Decision (2026-11-17): no timeout.** No Celery time limit, no timeout on the forecast `subprocess.Popen` (`forecast_runner.run_rscript`), none on the calls the `etl/` scripts make to other instances: job durations are never static, and a forecast can take well over 10 minutes. Not an issue; do not add one.
- *Fixed (2026-11-17), by liveness:* a killed worker (or an API restart during an inline `post_forecast` / `update_key`) still keeps the pipeline lock, which never expires, but `DELETE /pipeline/lock` (admin, Journal) now asks first. `TaskLauncher.is_active` looks for the job among the workers' tasks (`query_task`; Celery tasks are queued with `task_id=job_id`) and among the inline jobs of this API process (`analytics_service.RUNNING_INLINE`). Not running → freed at once; running, or no worker answering → 409 `confirmation_required` (`impact` `{job_id, task, active: true | null}`), shown by the Journal as a confirmation modal, then `confirm=true`. The release only frees the job asked about (`release_lock(job_id)`). Nothing is released automatically.
- **P3 — Limits of the liveness check.** (a) A task still in the broker queue while a worker is alive but has not prefetched it yet is seen as not running (a window of milliseconds after a launch). (b) A released job whose task is still queued runs later without the lock (it was so before). (c) `RUNNING_INLINE` is per process: right with a single API process (`run_server.py`). (d) The question waits Celery's default 1 s for the workers' replies (a limit on the question, not on any job). Imports resend the same `dataValueSets` each time.
- *Fixed (2026-10-09):* `etlui` no longer marks a step `success` on the 202: `usePipeline.ts` only shows an "accepted" toast and reads every status from `GET /pipeline/checkpoints`.
- *Fixed (2026-10-21):* forecast logs are no longer written only at the end: `run_rscript` reads `docker run` line by line, appends each line to the history (`JobStore.append_logs`) then publishes it.
- *Fixed (2026-11-17):* swallowed errors are logged at `WARNING`, the control flow unchanged (a storage failure still never fails the job): `JobStore` (each Redis and file operation), pub/sub publishing in `tasks.py` and `forecast_runner.py`, the forecast status file, the removal of the forecast env file, `notify_webhook` (host and exception type only: the URL may carry a token). The gate's `finish()` was already logged. `JobStore` has its own logger, on the real stderr and not propagating to root: during a job the root handler writes into the job's `_JobLogger` (next item), whose `write()` calls `append_logs`, so a failure logged through root looped until `RecursionError` (reproduced by the test with the isolation removed). Tests: `tests/infrastructure/test_swallowed_errors.py`.
- **P3 — Root logging is rebound to the last job.** Each script calls `etl/scripts/config.setup_logging()` inside the job: `basicConfig(force=True)` under `redirect_stderr` replaces every root handler (Celery's included) by one on that job's `_JobLogger`, and nothing restores them. That is how script logs reach the job log, but after the job every warning of the process that goes through root (API after an inline job, worker between jobs) is appended to the log of the last job. Possible fix in etlhub: `_execute_etl_job` saves the root handlers and level and restores them at the end. *Unverified:* the effect on Celery's own task loggers.
- **P3 — Still silent**: `_JobLogger.write` ignores a failed pub/sub publish (the line is already in the history). While Redis is down, `append_logs` and `publish_log` log one warning per job output line.
- *Fixed (2026-11-17):* `validate_inputs` errors no longer reach the job message empty. `etl/scripts/validate_inputs.py` raises `ValidationError` without a message, so `etl_use_cases._reason` falls back to its `errors` (then to the exception type) for every job.
- **P3 — Test mode offers one `external_data` fixture for every level** (`infrastructure/default_files.py`: `external_data/{level}` → `test/inputs/external_data.csv`). Its orgUnits are CSB ones, so an fkt run that takes the default now fails at `validate_inputs` (no orgUnit in common, since 2026-11-17) instead of forecasting on empty covariates; test mode still has no fkt fixture. Same ticket, side issue 1.
- **P3** — `run_rscript` rewrites the job record with a new `started` before `_run_task` writes the final status.
- **P3** — Whether `update_key` calls DHIS2 with `DRYRUN=true` depends on `pivot_dhis_tools` (not in the repo, *unverified*). Target (2026-10-12): test mode passes `DRYRUN=True` to `import_gee` and `post_forecast` only, as distinct from each `pridec` command's own `DRYRUN` option.
- **P2 — Pipeline revision of 2026-10-12, partly applied.** Not done: `calc_orgunit_alerts` (501, no script in `etl/scripts/`; meanwhile `POST /pipeline/runs/current/skip_alerts` marks the item done so CSB runs can complete), Done on 2026-11-17: the test-mode scope, replaced by an optional DRYRUN per launch (each launch of a job that writes to DHIS2 (`domain/pipeline.DHIS2_WRITES`: the 3 imports, `build_analytics`, `post_forecast`, `update_key`) takes an optional `dry_run`; absent, `true` in test mode, else `DRYRUN` of `.env` (`PipelineGate.default_dry_run`); the job's value is journaled (`launched` `dry_run`) and read by the scripts through `script_config._get` (`core/job_context.job_dry_run`, for that job only); `update_key` in dry run is refused (409: `pivot_dhis_tools` ignores its `dryRun`)); the level check of `external_data.csv`, at `validate_inputs` (`validation_use_cases._check_external_data_level`: the fkt and csb files have the same columns, so it refuses an `external_data` sharing no orgUnit with `disease_data.json`); `forecast_start` = the cycle, decided. See `decision-design/pipeline-checkpoints/pipeline-checkpoints.md` §6 and §8.
- **P3 — Schema migrations by hand (2026-11-04)**: the workers check the schema version at their first pipeline transaction, not at start; `request_log` is outside the versioning; the backup does not hold the files a migration moves (`input/`, `output/`, `uploads/`). See `decision-design/db-migrations/db-migrations.md`, "Limits".
- **Since 2026-10-08** `Settings` reads the root `.env` by default; `ENV_FILE` overrides it (VS Code debug configurations use `.env.debug`). Values exported in the process environment override the file. **Pending migration:** `.env.debug` is meant for local debugging only; decide what it keeps and align the launch configurations.

Fixed (request tracking, 2026-10-08): unhandled errors are recorded (500 + `error`), `/api/tracking` is never recorded, writes run off the event loop, SQLite only with a 30-day purge (the Redis copy `req:{id}` and the unused `services` / `track_service` are removed), each entry has a `timestamp`; `etlui` `/tracking` shows the data (`storeToRefs`), loads the last 50 requests on mount and on Refresh (no polling, 10 per page, so pagination works), shows the real time and the endpoint, and opens the logs of a request's job (`job_id` read from its JSON response) in a modal · `logs/requests/` (658 legacy files) deleted.

Fixed (checked 2026-11-04): `threading.local` is gone from `api/middleware.py` · a missing `.env` marks the forecast job `error` with `.env file not found: … (check HOST_PWD)` · `build_analytics` honours `DRYRUN` (logs and builds nothing).

Fixed: one shared Redis client per process (`infrastructure/redis_client.py`) replaces the per-instance clients · request tracking is stored in SQLite, so `list_recent` is one indexed query · `ValidationError` is now raised (input upload).

## 4. Dead code and duplication

Fixed: the five separate Redis clients · (2026-10-23) `get_request_tracker_repo` (now returns the middleware's tracker, one per process), `verify_signature`, the duplicated `_get_output_dir` and signature check, the `__import__(...)` calls in `forecast_runner.py`.

## 5. Tests

- 2026-11-17: 287 pass, 1 skipped. Coverage of the sources (`api`, `application`, `core`, `domain`, `infrastructure`) was **91 %** on 2026-11-04; `job_store.py` 49 %, `websockets/etl_logs.py` 80 %, auth 84–95 %.
- *Fixed (2026-11-17):* three tests of `tests/infrastructure/test_checkpoint_store.py` expected cycle `202610` without the `month` fixture, so they read the real month and failed since 2026-11. They now take the fixture.
- ~~**P3** — `etlhub/pytest.ini` used `[tool:pytest]`, so the file was ignored.~~ Fixed 2026-10-21: header renamed to `[pytest]` (CI broke on `No module named 'tests'` without its `pythonpath = .`).
- **P3** — `test_tracking_router.py:10,22,34` patch `etlhub.core.dependencies.get_tracking_service`, which has no effect; the tests pass thanks to `override_dependencies`.
- **P3** — Redis is a global `MagicMock` in `conftest.py`; only the auth tests use an in-memory fake. A green test says nothing about real Redis behaviour (the auth store was checked once against a real Redis 7.0.15 by hand).
- **P3** — `conftest.py` mocks `earthengine_api` but not `ee`. `ee` is imported only inside a function of `etl/scripts/import_gee.py`, so a test breaks only if it runs that function. No linter, formatter or type checker, no git hook. CI runs `pytest --cov` without threshold.
- **P3** — `etlui`: 27 spec files, but no `test` script in `package.json` (run `npx vitest run`), no eslint.

Fixed: the order-dependent `test_auth.py` failure (file rewritten) · tests no longer write into `logs/requests/` (SQLite in `tmp_path`); the 658 files still in `logs/requests/` are leftovers and can be deleted.

## 6. Documentation and config drift

- **P3** — The root `GETTING_STARTED.md:86-90` says port 8000; `run_server.py` uses 8111.
- **P3** — The root `.env.example` lacks `LOGS_DIR`, `DATA_DIR`, `HOST_PWD`, `ENV_FILE`, and has `GEE_PROJECT =` with a space.
- **P3** — `.env.debug` duplicates most of `.env` with different values for `DHIS_TOKEN`, `PIVOT_URL`, `PIVOT_TOKEN`, `LOG_LEVEL` (names compared on 2026-10-08). To clean up with the `.env.debug` migration.
- **P3** — `.claude/skills/etlhub/` holds `SKILL.md` (108 lines) and `implementation.md` (223 lines); `SKILL.md` never names `implementation.md`, so it is probably never loaded. Whether their contents diverge is *unverified*.
- **P3** — Version drift: `pridec_gee` is v0.2.0 in `etlhub/requirements.txt` and v0.2.1 in `etl/requirements.txt` (`pivot_dhis_tools` v0.1.2 in both).
- **P3** — `etlhub/CLAUDE.MD` is in upper case; the root `CLAUDE.md` points to `etlhub/CLAUDE.md`.
- **P3** — `compose.yaml` has no etlhub and no Redis; no etlhub Dockerfile.
- **P3** — `local-docs/` (git-ignored) contradicts the code in many places (auth, Redis, tests); do not trust it.

Fixed: `etlui/CLAUDE.md` now describes etlui · `.env.example` writes `DRYRUN` · the root `.env` declares `DHIS_URL` once.

## 7. Open questions

- A rebuilt `mvevans89/pridec_etl` image was not built or run. Since 2026-10-22 `etl/scripts/config.py` no longer imports `etlhub` or `redis`, and the scripts import it relatively (`from .config`); checked by `tests/infrastructure/test_dhis2_credential.py` and by running each `cli.sh` command's `--help` in the image layout (`/app/scripts` only).
- Celery pool and concurrency in production (default prefork)? How is etlhub deployed, and over http or https (`COOKIE_SECURE`)?
- Front/back mismatch on JSON bodies for `/fetch_disease` and `/validate_inputs`: fix the front or the back?
- `DRYRUN` and `LOG_LEVEL` are read from Redis by the scripts but cannot be edited through `/api/config`. Intended? (Since 2026-10-20 etlhub no longer writes `DRYRUN`: the test mode is `TEST_MODE`, see `decision-design/dry-run/dry-run.md`.)
- In which working directory does the worker run? Scripts write under `os.getcwd()/input|output`, so this decides where `input/` and `output/` land (*unverified*).
- `README.md` mentions `compose-prod.yaml`, which is not in the repository.
- Which tolerated imports become official (section 2)? Test-first for all new code? See `DEVELOPMENT.md`.
- Is the main branch protected on GitHub? Not visible in the repository.
