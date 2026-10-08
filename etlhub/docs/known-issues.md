# etlhub — Known issues

Checked against the code on 2026-10-08, after the DHIS2 login and route protection work (commit `9f66b09` and follow-ups). Items marked *unverified* come from reading the code only. Fixed items are listed at the end of each section so the history stays readable.

Priority scale: **P1** fix next (security or a broken feature), **P2** fix soon (wrong behaviour, data integrity), **P3** when convenient.

## 0. Priorities at a glance

| # | Priority | Issue | Section |
|---|---|---|---|
| 1 | P3 | `DELETE /output/reset`: "signature" is only "file exists" (sudo fallback removed) | 1.1 |
| 2 | P1 | `webhook_url`: SSRF from the worker (any URL, redirects followed) | 1.2 |
| 3 | P1 | `/validate_inputs`: free file paths and `input_dir` | 1.3 |
| 4 | P1 | Log WebSocket busy-waits (`get_message` without timeout) | 3 |
| 5 | P1 | `/post_forecast`, `/update_key` block the event loop | 3 |
| 6 | P2 | A login while a job runs revokes the token that job uses | 1.4 |
| 7 | P2 | No roles: any DHIS2 user of an allowed host can log in and run anything | 1.5 |
| 8 | P2 | No timeout, no reconciliation, no lock on jobs | 3 |
| 9 | P2 | Full URL (query string) stored in request logs | 1.6 |
| 10 | P2 | `etlui` marks a step `success` on the 202; forecast logs only at the end | 3 |
| 11 | P3 | Everything else below | — |

Order of work suggested: 2 → 3 (small, independent, each its own change), then 4 and 5 (they degrade the whole API), then 6 (needs a product decision).

## 1. Security

1. **P3 — `DELETE /output/reset`** (`api/routers/forecast_report_router.py`). Behind the session; the "signature" only checks that `.output_sig` exists and is non-empty. The `sudo rm -rf` fallback is gone (2026-10-08): forecast containers run as the worker's user (`forecast_runner._container_user`), `output/` is created by the worker before `docker run`, and the endpoint deletes with `shutil.rmtree` only. Files left root-owned by older runs must be handed back once (`GETTING_STARTED.md`, "output/ owned by root"). *Unverified:* the `PRIDEC` R package (not in the repo) is assumed to write only under `output/` and `HOME` (`/tmp`); a forecast run as non-root has not been executed yet.
2. **P1 — SSRF through `webhook_url`** (`infrastructure/tasks.py:24-38`). Any logged-in user can make the worker (host network) POST to any URL: no scheme or host check, and `urllib.request.urlopen` follows redirects. Fix: one validator (allowed hosts, https), called at launch; see migration m4.
3. **P1 — `/validate_inputs` takes free paths** (`api/routers/etl/validation_router.py:24-31`, `validation_use_cases.py:36`). File paths and `input_dir` come from the query; the use case writes `config_valid.json`, `input_valid.json`, `polygon_valid.geojson` into `input_dir`. Fix: reuse the `ForecastParams` path validator (under `input/`, no `..`, no leading `-`).
4. **P2 — A login revokes the token of running jobs.** Scripts read the DHIS2 token once at start (`DHIS_TOKEN = get_dhis_token()`). A new login revokes it (`api/auth/router.py`, `_revoke_previous`), so a running import gets 401 from DHIS2 mid-way and stops half done. Same at logout and at the 24 h expiry. Decision needed: refuse login/logout while a DHIS2 job runs (409), or document it.
5. **P2 — No roles.** Any user of a host in `DHIS2_ALLOWED_HOSTS` who can log in becomes the global DHIS2 identity for every job, and can call every endpoint (`DELETE /output/reset`, `/forecast/`, DHIS2 writes). Decision needed: require a DHIS2 authority or user group at login?
6. **P2 — Request logs keep the full URL** (`api/middleware.py:94-107`, stored in SQLite `logs/etlhub.db` and Redis `req:{id}`). A secret in a query string (a `webhook_url` carrying a token) is stored. Bodies and headers are not logged, so the login password and cookies are not.
7. **P3 — `X-Request-ID` is taken from the client** (`api/middleware.py:86`) and stored with `INSERT OR REPLACE` (`request_tracker.py:58`): a client can overwrite another request's log entry. No length limit. Fix: accept only a UUID. (The old path traversal risk is gone: the tracker no longer writes one file per request.)
8. **P3 — The DHIS2 token is in clear in Redis** (`dhis2:credential`) and in its AOF/RDB files. Accepted: `redis.conf` binds to localhost, requires a password, and the data directory must stay `chmod 700`. The token lives 24 h and is revoked at logout.
9. **P3 — Public pages to decide**: `GET /`, `/docs`, `/redoc`, `/openapi.json` (the full API map).
10. **P3 — Forecast temp env file** `/tmp/forecast_{id}.env` holds the other `.env` secrets (`PIVOT_TOKEN`, GEE…) for the whole run and survives a SIGKILL. It no longer contains `DHIS_URL` / `DHIS_TOKEN`.

Fixed (2026-10-08): every router except `auth_router` requires the session, the log WebSocket included (origin check, close `4401`), guarded by `tests/api/test_route_protection.py` · `GET /api/config/` no longer returns the DHIS2 token · OAuth routes, `/auth/validate-token` and `JWT_SECRET` removed · login sends credentials only to `DHIS2_ALLOWED_HOSTS` · failed login after revoking the previous token no longer leaves it active in Redis.

## 2. Layering violations

| Violation | Where |
|---|---|
| application → api | `application/use_cases/etl_use_cases.py`, `validation_use_cases.py` (`etlhub.api.etl_events`) |
| infrastructure → api | `infrastructure/tasks.py`, `forecast_runner.py` (`get_etl_event_manager`) |
| core → api | `core/dependencies.py:8` (unused `get_etl_event_manager` import) |
| api → infrastructure without DI | `api/routers/config_router.py:9-10`, `api/middleware.py`, and since the login work `api/auth/dhis2_auth.py:17`, `api/auth/router.py:21-22` (`auth_store`, `ConfigStore`) |
| etl scripts → etlhub infrastructure | `etl/scripts/config.py:3-4` (`ConfigStore`, `auth_store`) |
| application → pandas/geopandas | `validation_use_cases.py` |

The `EventPublisher` port exists in `domain/interfaces/` but is never injected. Proposed fix: move `ETLEventManager` to `infrastructure/` and inject it. The auth code follows the existing `config_router` pattern (direct infrastructure calls); whether that is tolerated is the same open decision as the other imports (see `DEVELOPMENT.md`).

## 3. Behaviour worth knowing

- **P1 — Log WebSocket busy-waits** (`api/websockets/etl_logs.py:130`): `pubsub.get_message()` is called with its default `timeout=0.0`, so the loop spins and the 30 s `wait_for` never fires. If the job ends between the status read and `subscribe`, the client waits forever. *Unverified at runtime.*
- **P1 — `/post_forecast` and `/update_key` run inline** in `async def` handlers (`analytics_router.py:56,109` → `analytics_service.py:22,38`): the whole API, login and WebSockets included, is frozen while they run.
- **P2 — No timeout, no reconciliation, no lock.** No Celery time limit, no timeout on the forecast `subprocess.run` (`forecast_runner.py:111`). A killed worker leaves `job:{id}` at `running` until the 24 h TTL. Two simultaneous `fetch_*`, `validate_inputs` or `forecast` runs write the same `input/` and `output/` files. Imports resend the same `dataValueSets` each time.
- **P2 — `etlui` marks a step `success` on the 202** (`useEtlPipeline.ts`), and **forecast logs are written only at the end** (`forecast_runner.py`): a WebSocket opened during a forecast gets `4004`, a clean close that `etlui` does not retry.
- **P2 — Swallowed errors**: `JobStore`, `RequestTracker.save` (Redis part) and pub/sub publishing catch every exception.
- **P3** — ETL failure: `save_logs` overwrites the job log with the traceback (`tasks.py`, `job_store.py`).
- **P3** — Forecast status written and published twice; `task_forecast` duplicates `_run_task`. `run_rscript` rewrites the job record with a new `started`.
- **P3** — `api/middleware.py:61`: `threading.local` shared across asyncio requests.
- **P3** — `forecast_runner._build_dynamic_env_file` opens `.env` without checking it exists (the job is marked `error` before Docker, see the test).
- **P3** — `build_analytics` ignores `DRYRUN`. Whether `update_key` calls DHIS2 with `DRYRUN=true` depends on `pivot_dhis_tools` (not in the repo, *unverified*).
- **P3** — Scripts write under `os.getcwd()/input|output`; the worker's cwd is *unverified*.
- **P3** — `TaskLaunchError` has a handler (`main.py`) but nothing raises it.
- **Verified 2026-10-08**: `Settings` reads only the file named by `ENV_FILE` (default `etlhub/.env`, which does not exist); the root `.env` is not read. The team keeps exporting `ENV_FILE` by hand (`GETTING_STARTED.md`). Values exported in the process environment (or loaded by `load_dotenv` before the first `get_settings()`) override the file.

Fixed: one shared Redis client per process (`infrastructure/redis_client.py`) replaces the per-instance clients · request tracking is stored in SQLite, so `list_recent` is one indexed query · `ValidationError` is now raised (input upload).

## 4. Dead code and duplication

- **P3** Dead: `track_service` (`api/middleware.py:65`), `ValidationResponse`, `BaseSchema`, `get_request_tracker_repo` (`core/dependencies.py:31`), `verify_signature` (`forecast_runner.py:66`), the `get_etl_event_manager` import in `core/dependencies.py`, `import uuid` in `validation_router.py`.
- **P3** Duplicated: `_get_output_dir` and the signature check (`forecast_runner.py` and `forecast_report_router.py`), ten near-identical Celery tasks, `__import__(...)` used 4 times in `forecast_runner.py` to call `get_settings`.

Fixed: the five separate Redis clients.

## 5. Tests

- 102 tests pass, 1 integration test deselected. Coverage of the sources (`api`, `application`, `core`, `domain`, `infrastructure`) is **70 %**; `infrastructure` 61 %, `etl_logs.py` 23 %, `job_store.py` 26 %, auth 83–95 %.
- **P3** — `etlhub/pytest.ini` uses `[tool:pytest]`: the file is ignored, hence the `PytestUnknownMarkWarning` for `integration`. Fix: rename the header to `[pytest]`.
- **P3** — `test_tracking_router.py:10,22,34` patch `etlhub.core.dependencies.get_tracking_service`, which has no effect; the tests pass thanks to `override_dependencies`.
- **P3** — Redis is a global `MagicMock` in `conftest.py`; only the auth tests use an in-memory fake. A green test says nothing about real Redis behaviour (the auth store was checked once against a real Redis 7.0.15 by hand).
- **P3** — `conftest.py` does not mock `ee`. No linter, formatter or type checker, no git hook. CI runs `pytest --cov` without threshold.
- **P3** — `etlui`: 7 spec files, 44 tests, but no `test` script in `package.json` (run `npx vitest run`), no eslint.

Fixed: the order-dependent `test_auth.py` failure (file rewritten) · tests no longer write into `logs/requests/` (SQLite in `tmp_path`); the 658 files still in `logs/requests/` are leftovers and can be deleted.

## 6. Documentation and config drift

- **P3** — `GETTING_STARTED.md:90-94` says port 8000; `run_server.py` uses 8111. The "Complete Setup" section runs `yarn start`; the script is `dev`.
- **P3** — `.env.example` lacks `LOGS_DIR`, `DATA_DIR`, `HOST_PWD`, `ENV_FILE`, and has `GEE_PROJECT =` with a space.
- **P3** — `REDIS_PASSWORD` differs between the local `.env` and `.env.debug` (seen on 2026-10-08); only `.env.debug` matches `redis-secret.conf`.
- **P3** — Two diverging versions of the skill: `etlhub/docs/SKILL.md` and `.claude/skills/etlhub/implementation.md` (probably not loaded: not named `SKILL.md`).
- **P3** — Version drift: `pridec_gee` and `pivot_dhis_tools` differ between `etlhub/requirements.txt` and `etl/requirements.txt`. The OpenAPI text of `/forecast/` says `:latest`, the code uses `:0.1.0`.
- **P3** — `etlhub/CLAUDE.MD` is in upper case; the root `CLAUDE.md` points to `etlhub/CLAUDE.md`.
- **P3** — `compose.yaml` has no etlhub and no Redis; no etlhub Dockerfile; `hubcenter.egg-info/` has no `setup.py`/`pyproject.toml`.
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
