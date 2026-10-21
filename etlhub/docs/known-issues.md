# etlhub — Known issues

Checked against the code on 2026-10-08, after the DHIS2 login and route protection work (commit `9f66b09` and follow-ups). Items marked *unverified* come from reading the code only. Fixed items are listed at the end of each section so the history stays readable.

Priority scale: **P1** fix next (security or a broken feature), **P2** fix soon (wrong behaviour, data integrity), **P3** when convenient.

## 0. Priorities at a glance

| # | Priority | Issue | Section |
|---|---|---|---|
| 1 | P3 | `DELETE /output/reset`: "signature" is only "file exists" (sudo fallback removed) | 1.1 |
| 5 | P1 | `/post_forecast`, `/update_key` block the event loop | 3 |
| 6 | P2 | A login while a job runs revokes the token that job uses | 1.4 |
| 7 | P2 | No roles: any DHIS2 user of an allowed host can log in and run anything | 1.5 |
| 8 | P2 | No timeout, no reconciliation, no lock on jobs | 3 |
| 9 | P2 | Full URL (query string) stored in request logs | 1.6 |
| 10 | P2 | `etlui` marks a step `success` on the 202; forecast logs only at the end | 3 |
| 11 | P3 | Everything else below | — |

Order of work suggested: 5 (it freezes the whole API), then 6 and 7 (they need a product decision).

## 1. Security

1. **P3 — `DELETE /output/reset`** (`api/routers/forecast_report_router.py`). Behind the session; the "signature" only checks that `.output_sig` exists and is non-empty. The `sudo rm -rf` fallback is gone (2026-10-08): forecast containers run as the worker's user (`forecast_runner._container_user`), `output/` is created by the worker before `docker run`, and the endpoint deletes with `shutil.rmtree` only. Files left root-owned by older runs must be handed back once (`GETTING_STARTED.md`, "output/ owned by root"). *Unverified:* the `PRIDEC` R package (not in the repo) is assumed to write only under `output/` and `HOME` (`/tmp`); a forecast run as non-root has not been executed yet.
2. *Fixed (2026-10-16):* SSRF through `webhook_url`. Every route takes the `WebhookUrl` type (`api/routers/__init__.py`): https to a host of `WEBHOOK_ALLOWED_HOSTS` only, 422 otherwise; empty list = every webhook refused. `notify_webhook` uses httpx, which does not follow redirects. *Unverified:* a DNS name of the allow-list that resolves to an internal address is still called.
3. *Fixed (2026-10-16):* `/validate_inputs` free paths. Its paths and `input_dir` take the `InputPath` type shared with `ForecastParams` (file path under `input/`, no `..`, no leading `-`), and the use case resolves them against the repo root instead of the worker's cwd.
4. **P2 — A login revokes the token of running jobs.** Scripts read the DHIS2 token once at start (`DHIS_TOKEN = get_dhis_token()`). A new login revokes it (`api/auth/router.py`, `_revoke_previous`), so a running import gets 401 from DHIS2 mid-way and stops half done. Same at logout and at the 24 h expiry. Decision needed: refuse login/logout while a DHIS2 job runs (409), or document it.
5. **P2 — No roles.** Any user of a host in `DHIS2_ALLOWED_HOSTS` who can log in becomes the global DHIS2 identity for every job, and can call every endpoint (`DELETE /output/reset`, `/forecast/`, DHIS2 writes). Decision needed: require a DHIS2 authority or user group at login?
6. **P2 — Request logs keep the full URL** (`api/middleware.py:94-107`, stored in SQLite `logs/etlhub.db`, 30 days). A secret in a query string (a `webhook_url` carrying a token) is stored. Bodies and headers are not logged, so the login password and cookies are not.
7. *Fixed (2026-10-08):* a client `X-Request-ID` is kept only if it is a UUID (`api/middleware.py`, `_request_id`), so it can no longer overwrite another entry.
8. **P3 — The DHIS2 token is in clear in Redis** (`dhis2:credential`) and in its AOF/RDB files. Accepted: `redis.conf` binds to localhost, requires a password, and the data directory must stay `chmod 700`. The token lives 24 h and is revoked at logout.
9. **P3 — Public pages to decide**: `GET /`, `/docs`, `/redoc`, `/openapi.json` (the full API map).
10. **P3 — Forecast temp env file** `/tmp/forecast_{id}.env` holds the other `.env` secrets (`PIVOT_TOKEN`, GEE…) for the whole run and survives a SIGKILL. It no longer contains `DHIS_URL` / `DHIS_TOKEN`.

Fixed (2026-10-08): every router except `auth_router` requires the session, the log WebSocket included (origin check, close `4401`), guarded by `tests/api/test_route_protection.py` · `GET /api/config/` no longer returns the DHIS2 token · OAuth routes, `/auth/validate-token` and `JWT_SECRET` removed · login sends credentials only to `DHIS2_ALLOWED_HOSTS` · failed login after revoking the previous token no longer leaves it active in Redis.

## 2. Layering violations

| Violation | Where |
|---|---|
| application → api | `application/use_cases/etl_use_cases.py` (`etlhub.api.etl_events`) |
| infrastructure → api | `infrastructure/tasks.py`, `forecast_runner.py` (`get_etl_event_manager`) |
| api → infrastructure without DI | `api/routers/config_router.py:9-10`, `api/middleware.py`, and since the login work `api/auth/dhis2_auth.py:17`, `api/auth/router.py:21-22` (`auth_store`, `ConfigStore`) |
| etl scripts → etlhub infrastructure | `etl/scripts/config.py:3-4` (`ConfigStore`, `auth_store`) |
| application → pandas/geopandas | `validation_use_cases.py` |

There is no event port. Proposed fix: move `ETLEventManager` to `infrastructure/` behind a port and inject it. The auth code follows the existing `config_router` pattern (direct infrastructure calls); whether that is tolerated is the same open decision as the other imports (see `DEVELOPMENT.md`).

## 3. Behaviour worth knowing

- *Fixed (2026-10-08):* the log WebSocket no longer busy-waits (1 s `get_message` timeout, 0.3 % CPU measured while waiting), subscribes before reading history, re-checks the job status every 10 s, stops when the client leaves, and closes with `4004` only for an unknown job. Jobs are recorded `pending` at launch. The tracking page follows pending/running jobs live in its request detail modal.
- **P1 — `/post_forecast` and `/update_key` run inline** in `async def` handlers (`analytics_router.py:56,109` → `analytics_service.py:22,38`): the whole API, login and WebSockets included, is frozen while they run.
- **P2 — No timeout, no reconciliation, no lock.** No Celery time limit, no timeout on the forecast `subprocess.run` (`forecast_runner.py:111`). A killed worker leaves `job:{id}` at `running` until the 24 h TTL. Lock: fixed since 2026-10-08 (one job at a time, `docs/decision-design/pipeline-checkpoints/pipeline-checkpoints.md`); it never expires, so a killed worker blocks everything until `DELETE /pipeline/lock`. `DELETE /output/reset` still bypasses it. Imports resend the same `dataValueSets` each time.
- *Fixed (2026-10-09):* `etlui` no longer marks a step `success` on the 202: `usePipeline.ts` only shows an "accepted" toast and reads every status from `GET /pipeline/checkpoints`.
- **P2 — Forecast logs are written only at the end** (`forecast_runner.py`): a WebSocket opened during a forecast gets status updates but no log lines until the end.
- **P2 — Swallowed errors**: `JobStore` and pub/sub publishing catch every exception. So does the gate's `finish()` at the end of a job (logged, on purpose: the job keeps its real status, and the lock then needs `DELETE /pipeline/lock`).
- **P3** — `run_rscript` rewrites the job record with a new `started` before `_run_task` writes the final status.
- **P3** — `api/middleware.py:61`: `threading.local` shared across asyncio requests.
- **P3** — `forecast_runner._build_dynamic_env_file` opens `.env` without checking it exists (the job is marked `error` before Docker, see the test).
- **P3** — `build_analytics` ignores `DRYRUN`. Whether `update_key` calls DHIS2 with `DRYRUN=true` depends on `pivot_dhis_tools` (not in the repo, *unverified*). Target (2026-10-12): test mode passes `DRYRUN=True` to `import_gee` and `post_forecast` only, as distinct from each `pridec` command's own `DRYRUN` option.
- **P2 — Pipeline revision of 2026-10-12, partly applied.** Not done: `calc_orgunit_alerts` (501, no script in `etl/scripts/`, so CSB runs and the cycle cannot complete), the test-mode scope (`DRYRUN` stays global), and the level check of `external_data.csv` (columns unknown). `forecast_start` is written as the cycle month until `pivot_forecast.sh`'s value is confirmed. See `decision-design/pipeline-checkpoints/pipeline-checkpoints.md` §6 and §8.
- **P3** — Scripts write under `os.getcwd()/input|output`; the worker's cwd is *unverified*.
- **Since 2026-10-08** `Settings` reads the root `.env` by default; `ENV_FILE` overrides it (VS Code debug configurations use `.env.debug`). Values exported in the process environment override the file. **Pending migration:** `.env.debug` is meant for local debugging only; decide what it keeps and align the launch configurations.

Fixed (request tracking, 2026-10-08): unhandled errors are recorded (500 + `error`), `/api/tracking` is never recorded, writes run off the event loop, SQLite only with a 30-day purge (the Redis copy `req:{id}` and the unused `services` / `track_service` are removed), each entry has a `timestamp`; `etlui` `/tracking` shows the data (`storeToRefs`), loads the last 50 requests on mount and on Refresh (no polling, 10 per page, so pagination works), shows the real time and the endpoint, and opens the logs of a request's job (`job_id` read from its JSON response) in a modal · `logs/requests/` (658 legacy files) deleted.

Fixed: one shared Redis client per process (`infrastructure/redis_client.py`) replaces the per-instance clients · request tracking is stored in SQLite, so `list_recent` is one indexed query · `ValidationError` is now raised (input upload).

## 4. Dead code and duplication

- **P3** Dead: `get_request_tracker_repo` (`core/dependencies.py`), `verify_signature` (`forecast_runner.py`).
- **P3** Duplicated: `_get_output_dir` and the signature check (`forecast_runner.py` and `forecast_report_router.py`), `__import__(...)` used 4 times in `forecast_runner.py` to call `get_settings`.

Fixed: the five separate Redis clients.

## 5. Tests

- 102 tests pass, 1 integration test deselected. Coverage of the sources (`api`, `application`, `core`, `domain`, `infrastructure`) is **70 %**; `infrastructure` 61 %, `etl_logs.py` 23 %, `job_store.py` 26 %, auth 83–95 %.
- ~~**P3** — `etlhub/pytest.ini` used `[tool:pytest]`, so the file was ignored.~~ Fixed 2026-10-21: header renamed to `[pytest]` (CI broke on `No module named 'tests'` without its `pythonpath = .`).
- **P3** — `test_tracking_router.py:10,22,34` patch `etlhub.core.dependencies.get_tracking_service`, which has no effect; the tests pass thanks to `override_dependencies`.
- **P3** — Redis is a global `MagicMock` in `conftest.py`; only the auth tests use an in-memory fake. A green test says nothing about real Redis behaviour (the auth store was checked once against a real Redis 7.0.15 by hand).
- **P3** — `conftest.py` does not mock `ee`. No linter, formatter or type checker, no git hook. CI runs `pytest --cov` without threshold.
- **P3** — `etlui`: 7 spec files, 44 tests, but no `test` script in `package.json` (run `npx vitest run`), no eslint.

Fixed: the order-dependent `test_auth.py` failure (file rewritten) · tests no longer write into `logs/requests/` (SQLite in `tmp_path`); the 658 files still in `logs/requests/` are leftovers and can be deleted.

## 6. Documentation and config drift

- **P3** — `GETTING_STARTED.md:90-94` says port 8000; `run_server.py` uses 8111.- **P3** — `.env.example` lacks `LOGS_DIR`, `DATA_DIR`, `HOST_PWD`, `ENV_FILE`, and has `GEE_PROJECT =` with a space.
- **P3** — `.env.debug` duplicates most of `.env` with different values for `DHIS_TOKEN`, `PIVOT_URL`, `PIVOT_TOKEN`, `LOG_LEVEL` (names compared on 2026-10-08). To clean up with the `.env.debug` migration.
- **P3** — Two diverging versions of the skill: `etlhub/docs/SKILL.md` and `.claude/skills/etlhub/implementation.md` (probably not loaded: not named `SKILL.md`).
- **P3** — Version drift: `pridec_gee` and `pivot_dhis_tools` differ between `etlhub/requirements.txt` and `etl/requirements.txt`.
- **P3** — `etlhub/CLAUDE.MD` is in upper case; the root `CLAUDE.md` points to `etlhub/CLAUDE.md`.
- **P3** — `compose.yaml` has no etlhub and no Redis; no etlhub Dockerfile.
- **P3** — `local-docs/` (git-ignored) contradicts the code in many places (auth, Redis, tests); do not trust it.

Fixed: `etlui/CLAUDE.md` now describes etlui · `.env.example` writes `DRYRUN` · the root `.env` declares `DHIS_URL` once.

## 7. Open questions

- Does a rebuilt `mvevans89/pridec_etl` image still work? `etl/scripts/config.py` imports `etlhub` (`ConfigStore`, `auth_store`), but `etl/Dockerfile` only copies `scripts/` and `etl/requirements.txt` has no `redis`. The CLI `.env` fallback (`DHIS_ENV_FALLBACK` in `compose.yaml`) depends on it.
- Login during a running job (1.4) and roles (1.5): which behaviour do we want?
- Celery pool and concurrency in production (default prefork)? How is etlhub deployed, and over http or https (`COOKIE_SECURE`)?
- Front/back mismatch on JSON bodies for `/fetch_disease` and `/validate_inputs`: fix the front or the back?
- `DRYRUN` and `LOG_LEVEL` are read from Redis by the scripts but cannot be edited through `/api/config`. Intended?
- In which working directory does the worker run? This decides where `input/` and `output/` land.
- `README.md` mentions `compose-prod.yaml`, which is not in the repository.
- Which tolerated imports become official (section 2)? Test-first for all new code? See `DEVELOPMENT.md`.
- Is the main branch protected on GitHub? Not visible in the repository.
