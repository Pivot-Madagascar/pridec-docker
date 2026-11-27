# Hexagonal architecture review of etlhub

Review 2026-11-26, confronted with `etlhub/CLAUDE.md` ("Rules", "Architecture", "Gotchas") and the decision docs on
2026-11-27. The owner decided every item on 2026-11-27; each item below says what was done ("Outcome 2026-11-27").

## Verdict

Measured against its own rules (`etlhub/CLAUDE.md`), etlhub respects its architecture almost everywhere. Most gaps
against a textbook hexagonal architecture are **choices made before**, written in `CLAUDE.md` or in a decision doc
(section A). What remains:

- 3 deviations from the letter of `CLAUDE.md`, none caught by `tests/test_architecture.py` (section B; B1 fixed
  2026-11-27);
- 3 points that `CLAUDE.md` does not cover (section C);
- drift between `CLAUDE.md` and the code (section D).

## Confrontation, rule by rule

| `etlhub/CLAUDE.md` rule | State | Evidence |
|---|---|---|
| `domain` imports nothing | Respected | `tests/test_architecture.py`; `domain/pipeline.py` pure |
| `application` imports `domain`, `core` settings | Partly | also `core.job_context`, `core.request_context` (A3); `core.dependencies` (B2) |
| `application` talks to the outside only through ports | Partly | ETL copies tolerated (A2); webhook and availability check outside the wording (A2, last rows) |
| `infrastructure` holds adapters implementing the ports | Respected, with A1 | `checkpoint_store.py` also holds the pass rules |
| `api` never imports `etlhub.infrastructure` | Respected | test, 2 passed |
| `api` gets services and adapters by injection: `Depends` in a route signature, direct getter call only in middleware, helpers, `get_current_user` | Deviation | `etl_logs.py` builds its own Redis client (B3); `config_router.py` (B1) fixed 2026-11-27 |
| `core/dependencies.py` is the only place that binds a port to its adapter | Not literally | `main.py`, `tasks.py`, `script_config.py`, `checkpoint_store.py` build adapters (A4) |
| A use case annotates its collaborators with ports | Respected | no `infrastructure` import in `application` |
| A new adapter method used by a use case or router goes into its port | Respected | every `gate.*` call in `api` / `application` is in `PipelineGate`; the 9 adapters (one per port) implement every method of their port (AST comparison, 2026-11-27) |
| A new adapter gets a port when `application/` uses it | Respected | the only adapter `application` reaches, `RedisFetchedImports`, has its port `FetchedImports` (reached through B2) |
| A port with a single adapter is normal | Respected | 9 ports kept |
| `ALLOWED_DEBT` empty, never extended | Respected | empty; the test's scope is narrower than the doc (B2, A4) |
| No type checker: keep adapters and fakes in sync by hand | Mostly kept | see "Port conformance" below |

### Port conformance (static comparison, 2026-11-27)

- Every adapter has every method of its port: `CheckpointStore`, `JobStore`, `CeleryTaskLauncher`, `RequestTracker`,
  `ConfigStore`, `RedisFetchedImports`, `DefaultFiles`, modules `auth_store` and `etl_events`.
- Naming drift: `PipelineGate.finish(job_id, status)` vs `CheckpointStore.finish(job_id, state)`. Every caller passes it
  positionally, so harmless today; a keyword call `status=` would fail.
- `CheckpointStore.pause` and `abandon` add optional parameters (`cause`, `reason`): compatible.
- `OpenGate` (`tests/conftest.py`) is a deliberately partial fake ("for tests that are not about the pipeline order"):
  9 of the 28 methods of `PipelineGate`; its `start` lacks `gee_variables`. Not exercised: `gate.start` is only called
  by `infrastructure/tasks.py`, on the real store.

## What conforms

- `domain` imports nothing outside itself; `domain/pipeline.py` is pure (rules R1–R6 as functions, no I/O).
- 9 `Protocol` ports in `domain/interfaces/`, bound for `api` and `application` in `core/dependencies.py`; services
  built per request with `Depends()`.
- `tests/test_architecture.py` passes (2 passed on 2026-11-26), `ALLOWED_DEBT` empty.
- Celery tasks (`infrastructure/tasks.py`) are a driving adapter calling `application`: correct direction.
- Ports are replaced in tests through `dependency_overrides` (`OpenGate`, `Liveness`, `job_store`).

## A. Choices made before (tracked, not defects)

Each one departs from a textbook hexagonal architecture, but was written down before: decided, or tolerated pending
the team's decision (A2). Kept here so that a change to the decision is a conscious one.

### A1. The pass rules live in the store: `infrastructure/checkpoint_store.py`

- What: 1334 lines (the whole `application/use_cases/` is 1233). `PipelineGate` has 28 methods, most of them business
  operations (`decide`, `decide_imports`, `skip_alerts`, `start_pass`, `pause`, `resume`, `abandon`, `leave_mode`, ...).
  25 `raise` of domain exceptions, rules such as `_check_config` (a launch on another DHIS2 than the pass's is
  refused), and side effects beyond storage (Redis config through `apply_to_config_store`, work files through
  `_save_work` / `_restore_work`).
- Where decided: `domain/pipeline.py` docstring (R3 and R6 "enforced by the store");
  `pipeline-checkpoints/pipeline-checkpoints.md` (a run is opened "in a single transaction") and its guide (the store
  holds the run context and empties `input/` / `output/`); `cycle-passes/cycle-passes.md` § 11 (carry-over "all in the
  launch's transaction"); `CLAUDE.md` Gotchas (every launch, upload and input delete goes through the pipeline gate,
  `CheckpointStore`; cycle journal written by `_event` "in the same transaction"; one job lock for both modes);
  `CLAUDE.md` "Method for new code" (reuse `CheckpointStore`).
- Why: atomicity. A refused launch writes nothing; check and write share one SQLite transaction.
- Residual: `CLAUDE.md` "Architecture" says `domain` holds the rules and never states this exception. Changing the
  storage means rewriting the pass rules; testing them needs SQLite (the `checkpoint_store` fixture provides it).
- Revisit if: a second storage is needed, or the pass rules must be tested without SQLite. Direction then: extend the
  pattern of `domain/pipeline.py` (pure functions on `Rows`) to the pass state machine.
- Outcome 2026-11-27: written in `CLAUDE.md` "Architecture" (A1 line), unchanged in the code.

### A2. ETL copies in `application` call DHIS2, Pivot and GEE directly

| File | Calls | Covered by the tolerance? |
|---|---|---|
| `build_analytics.py` | DHIS2 through `httpx` | yes: "etlhub's copy of etl/scripts/build_analytics.py", `ponytail:` marked |
| `calc_alerts.py` | `pivot_dhis_tools`, files only | yes: copy of `calc_orgUnit_alerts.py`, `ponytail:` marked |
| `post_forecast.py` | DHIS2 through `pivot_dhis_tools` | yes: copy of `post_forecast.py`, `ponytail:` marked |
| `fetch_pivot.py` | Pivot and DHIS2 through `pivot_dhis_tools` | yes: copy of `import_pivot_*_etlhub.py`, `ponytail:` marked |
| `gee_import.py` | GEE and DHIS2 | yes: version of `import_gee.py`, `ponytail:` marked |
| `validation_use_cases.py` | pandas / geopandas on files | yes: named in the tolerance |
| `check_import_availability.py` | DHIS2 through `requests` | **not by its wording**: no ETL script behind it (constants copied from them, `ponytail:` marked); its location is documented in `CLAUDE.md` Gotchas (`GET /import_availability`). **Outcome 2026-11-27: behind a port.** `DHIS2Reader` (`data_values`, `analytics`, `system_info`), adapter `infrastructure/dhis2_reader.py` (`HttpDHIS2Reader`), bound by `get_dhis2_reader`; the file keeps the plan and the copied constants. Then (owner's decision, 2026-11-27) its configuration went behind `ImportSettings` (adapter `infrastructure/import_settings.py`, `ScriptImportSettings`, over `etl/scripts/config.py`) and its periods are computed by `_last_months` (stdlib, checked against `create_period_range` by `tests/test_library_constants_sync.py`): it imports no ETL library any more |
| `etl_use_cases.py` (`notify_webhook`) | webhook through `httpx` | **no**: listed in the `CLAUDE.md` module map and `ARCHITECTURE.md` as part of `application`, but not in the tolerance, and it contradicts "only through ports". **Outcome 2026-11-27: behind a port.** `WebhookNotifier`, adapter `infrastructure/webhook_notifier.py` (`HttpWebhookNotifier`), passed by the worker (`tasks._run`); `etl_use_cases.py` no longer imports `httpx` |

- Where written: `CLAUDE.md` "Architecture": "Tolerated, pending the team's decision: `application` → `etl.scripts` and
  the libraries they need (the ETL wrappers ...)". The copies' debt is tracked by their `ponytail:` comments.
- Residual: `tests/conftest.py` replaces these libraries with a global `MagicMock`; the team decision is still pending.
- Outcome 2026-11-27: the tolerance is now enforced file by file (`THIRD_PARTY_FILES` in `tests/test_architecture.py`): only the ETL copies may import `etl`, `pivot_dhis_tools`, `pridec_gee`, `ee`, `pandas`, `geopandas`, `httpx` (`build_analytics.py`). Not an ETL copy, accepted by the owner on 2026-11-27 and named in the guard: `ingestion_service.py` → `pridec_gee.AVAILABLE_VARIABLES` (a constant list).

### A3. Mode and request context as `contextvars` in `core`

- What: `core/job_context.py` (`current_test_mode`, `work_dir`, `job_pass_config`) and `core/request_context.py` are
  read by `application`, `infrastructure` and `api`: inputs that pass through no port.
- Where decided: `CLAUDE.md` Gotchas "Mode per user and isolation" (every mode read through the `test_mode` callable,
  every path through `work_dir`) and "Cycle journal" (actor and `request_id` from `core/request_context.py`);
  `mode-isolation/mode-isolation.md`. Tolerated: "any layer → `core` settings".
- Residual: these modules are context, not settings; the tolerance's wording does not name them.
- Outcome 2026-11-27: named in `CLAUDE.md` "Architecture" (A3 line and table) and in the guard (`CORE_SHARED`).

### A4. Adapters built outside `core/dependencies.py`

- What: `main.py` lifespan (`ConfigStore().load_env()`, `get_checkpoint_store().check_schema()`);
  `infrastructure/tasks.py`, the worker side (`JobStore()`, `get_checkpoint_store()`, `etl_events` passed to
  `run_etl_job`); `infrastructure/checkpoint_store.py` (`ConfigStore()`); `etlhub/script_config.py` (Redis config,
  `get_checkpoint_store().pass_config()`, `auth_store.get_credential`).
- Where decided: `CLAUDE.md` (config copy in the `main.py` lifespan; `script_config.py` replaces `_get` /
  `_dhis2_credential` with Redis and the login; the pass config read by `script_config._get`);
  `pipeline-checkpoints.md` (`_update_task_status` calls `finish()`).
- Residual: `CLAUDE.md` calls `core/dependencies.py` "the only place that binds a port to its adapter"; true for `api`
  and `application` only. `script_config.py` is outside the four folders `tests/test_architecture.py` walks.
- Outcome 2026-11-27: written in `CLAUDE.md` "Architecture" (A4 line; table row for the composition roots). The guard
  now walks `core/`, `main.py`, `script_config.py`, `migrate.py` and the other root files, each with its rule.

## B. Deviations from the letter of `etlhub/CLAUDE.md`

None was caught by `tests/test_architecture.py`; since 2026-11-27 each would be.

### B1. Direct getter calls in route bodies: `api/routers/config_router.py`

**Fixed 2026-11-27 (recommendation 1).** `get_config_store()` (3 calls) and `get_auth_store()` (1 call) were called
inside routes. `CLAUDE.md` asks for `Depends(get_…)` in a route signature; direct calls are for middleware, helpers and
`get_current_user`. Cost: `app.dependency_overrides` could not replace them in tests. The three routes now get
`ConfigRepository` and `AuthStore` through `Depends`; the shared response is built by `_response(store, auth)`.
Guarded by `tests/api/test_config_router.py::test_the_routes_get_their_stores_by_injection` (failed before the fix).

### B2. Service locator from `application`: `fetch_pivot._store()`

`application/use_cases/fetch_pivot.py` imports `core.dependencies` at call time (its comment: "the jobs and the module
functions get no injection"); `gee_import.py` reuses `_store()`, and `api` reaches it through
`fetch_pivot.fetched_imports()` and `gee_import.gee_imports()`. `CLAUDE.md` lets `application` import `core` settings
only. The guard is wider than the doc: it allows all of `core`, and `core.dependencies` imports all of
`infrastructure`, so any `application` module could reach any adapter this way without the test failing.

**Outcome 2026-11-27: injected.** `_store()` is gone; the functions of `fetch_pivot.py` and `gee_import.py` take
`imports: FetchedImports`, given by the worker (`tasks.task_etl` builds `RedisFetchedImports()`) or by `Depends(get_fetched_imports)`
(`pipeline_router.py`, `AnalyticsService`). The guard refuses `application` → `core.dependencies`.

### B3. The log WebSocket builds its own Redis client: `api/websockets/etl_logs.py`

It creates a `redis.asyncio` pool and subscribes to pub/sub directly. `CLAUDE.md`: `api` "gets services and adapters by
injection". The `EventPublisher` port covers publishing, not subscribing. Invisible to the test, which checks `etlhub`
imports only.

**Outcome 2026-11-27: port.** `EventSubscriber` (`subscribe`, `next_event`, `close`), adapter `RedisEventSubscriber` in
`infrastructure/etl_events.py` (same channels, the async pool moved there), bound by `get_event_subscriber` and passed
with `Depends`. Nothing under `api/` imports `redis`; the guard refuses it.

## C. Not covered by `etlhub/CLAUDE.md`

- `api/routers/forecast_report_router.py` reads `output/forecast_report.html` and archives `output/` itself. It follows
  the path rule (`work_dir`); no port exists for output files. Same pattern as `PipelineGate.report()`, which returns a
  `Path` that the router serves. **Outcome 2026-11-27: port** `OutputFiles` (`report`, `archive`), adapter
  `infrastructure/output_files.py` (`WorkDirOutputFiles`), bound by `get_output_files`.
- `api/auth/router.py` catches `redis.RedisError` (2 places): an infrastructure exception reaches the API layer.
  `CLAUDE.md` mentions `except redis.RedisError` only as a test pitfall (Gotchas, `test_auth.py`), never as a choice.
  **Outcome 2026-11-27: domain exception.** `infrastructure/auth_store.py` turns `redis.RedisError` into
  `AuthStoreUnavailable` (`domain/exceptions.py`); the router catches that (same 503). Login's DHIS2 HTTP calls moved
  from `api/auth/dhis2_auth.py` behind the `DHIS2Accounts` port (`infrastructure/dhis2_accounts.py`), `DHIS2Error` to
  `domain/exceptions.py`.
- Third-party imports by layer: nothing says which libraries `api` or `domain` may import (`redis`, `sqlite3`, `httpx`).
  **Outcome 2026-11-27: rule and guard.** `CLAUDE.md` "Architecture" lists the libraries per layer;
  `tests/test_architecture.py` (`THIRD_PARTY`, `THIRD_PARTY_FILES`) enforces them (`sqlite3` is stdlib: allowed
  everywhere by the stdlib rule, used in `infrastructure` only today).

## D. Drift between `etlhub/CLAUDE.md` and the code

- Module map, ports: lists 8; the code has 9 (`FetchedImports` missing).
- Module map, `core/`: misses `job_context.py` and `request_context.py` (A3).
- Module map, `*_service.py` "generate `job_id`, call `CeleryTaskLauncher`": the services hold the `TaskLauncher` port,
  and `tracking`, `journal`, `availability` and `input_upload` services launch nothing.
- Module map, `infrastructure/`: misses `checkpoint_store.py`, `default_files.py`, `fetched_imports.py`,
  `redis_client.py`.
- Module map, `application/use_cases/`: misses `fetch_pivot.py`, `gee_import.py`, `build_analytics.py`,
  `calc_alerts.py`, `post_forecast.py`, `check_import_availability.py` (the `*_service.py` pattern covers the others).
- Module map, `tests/`: "`api/` and `infrastructure/`"; 8 test files also sit at the root of `tests/`, including
  `test_architecture.py`.
- Architecture table: `application` may import "`core` settings"; the test allows all of `core` (B2).
- Architecture table: `core/dependencies.py` "the only place" that binds; not true for the worker, `main.py` and
  `script_config.py` (A4).
- "Where to look next": the `decision-design/` list misses several folders, `hexagonal-review/` included.
- Outside architecture, seen in passing: "Required checks" lists `config_router`, the WebSocket, `RequestTracker` and
  `forecast_runner` as untested, but `tests/api/test_config_router.py`, `tests/api/test_etl_logs_ws.py`,
  `tests/infrastructure/test_request_tracker.py` and `tests/infrastructure/test_forecast_runner.py` exist (what they
  cover was not checked).

## Recommendations (owner's decision, one by one)

1. **Fix B1 (small). Done 2026-11-27.** `config_router.py`: the 4 getter calls moved to `Depends(...)` in the route
   signatures. No contract change. Test first (`tests/api/test_config_router.py`, through `app.dependency_overrides`);
   suite before 384 passed, after 385 passed.
2. **Decide B2.** Either inject `FetchedImports` into `fetch_pivot` / `gee_import`, or write the exception into
   `CLAUDE.md`. Then align the guard with the doc: allow `application` the `core` modules it is meant to use
   (`config`, `job_context`, `request_context`), not `core.dependencies`. Today this fails on `fetch_pivot.py` only.
   **Done 2026-11-27**: injected (B2) and the guard aligned (relative and one-part imports, `core/` and root files too).
3. **Decide B3.** A subscription port for the log WebSocket, bound in `core/dependencies.py`, or a written exception.
   **Done 2026-11-27**: port `EventSubscriber` (B3).
4. **Write the choices of section A into `CLAUDE.md` "Architecture"** (one line each): the store holds the pass rules
   (A1), the mode / request `contextvars` (A3), the adapters built by the worker, `main.py` and `script_config.py`
   (A4), and settle the webhook and the availability check (A2, last two rows): tolerated, or behind a port.
   **Done 2026-11-27**: A1, A3, A4 lines in `CLAUDE.md`; webhook and availability check behind ports (A2).
5. **Fix the drift of section D** in the `CLAUDE.md` module map and architecture table.
   **Done 2026-11-27** for the module map (14 ports, the new adapters) and the table (`core` modules per layer,
   composition roots, root files). Most other D items had been fixed before (module map already listed 9 ports).
6. **Optional, lower priority than first thought.** A type checker on `domain/interfaces`, `infrastructure` and
   `tests/conftest.py`: the static comparison shows every adapter in sync; only `finish`'s parameter name drifts.
   `CLAUDE.md` says of linters and formatters "none configured. Do not invent one": adding any such tool is the
   owner's explicit call. The cheaper fix is renaming `state` to `status` in `CheckpointStore.finish`.
   **Done 2026-11-27**: renamed (no type checker added); every caller passes it positionally, the fakes already said
   `status`.

## Not verified

- `checkpoint_store.py` and `pipeline_router.py` were not read in full (outline and samples only).
- Port conformance was compared by method names and parameter names (AST), not by types or behaviour.
- Only `tests/test_architecture.py` was run, not the full suite.
