# Mode isolation: what happens in one mode is never readable in the other

Status: implemented on 2026-11-19: lots 1 to 3 (first with a mode global to the server), then the mode per user and the per-mode folders (§ 5b, 5c, 7). Nothing run against a real etlhub, Redis, Celery or Docker: unit tests only.

## 1. Request

Owner request (2026-11-19): the test mode is a parameter of the whole application, chosen before the cycle; what
happens in one mode must never be accessible in the other. Scope chosen by the owner: the server refuses, etlui
follows; Journal, Tracking, Recent Activity, and separate `input/` / `output/`.

At first the mode was global to the server (`pipeline:test_mode` in Redis): switching it switched it for every user.
Since § 5c it is each user's, kept in their session; isolation is "the mode served reads only its own data".

## 2. Before

| Data | Separated by mode? |
|---|---|
| checkpoints, passes, runs, `availability_checks` | yes: SQLite file in production, Redis blob in test (`checkpoint_store.py`) |
| `GET /pipeline/cycles` | **no**: listed the passes of both stores (cycle-passes UC13) |
| `GET /pipeline/passes/{id}/journal[.csv]` | **no**: read both stores |
| `GET /api/tracking/requests[/{id}]` | **no**: `request_log` had no mode |
| `GET /api/tracking/etl-logs/{job_id}` and its WebSocket | **no**: any job id |
| Recent Activity (etlui, in memory) | **no**: kept across a switch on the Dashboard |
| `input/`, `output/` | **no**: shared (pass-folders F10, pipeline-checkpoints §4.10) |

## 3. Decisions

| # | Question | Decision |
|---|---|---|
| M1 | A pass, journal or job of the other mode | Read as unknown: empty journal (as an unknown pass already was), 404 for a request or job logs, WebSocket close `4004`. No new error code, no contract change. |
| M2 | Which mode a job belongs to | The journal of the current mode names it (`pipeline_events.job_id`, indexed): every launch goes through the gate, which writes `launched` before the 202. Works after the 24 h of `job:{id}` and without waiting for the request log. `PipelineGate.has_job`. |
| M3 | Which mode a request belongs to | `mode` in the request's JSON (`request_log.data`): the session's, set by `get_current_user` in `request_context` (since the mode per user; first read from the global key). `PUT /pipeline/mode` is listed in the mode it was sent from. No schema change. A request without session (login): no mode, listed nowhere. |
| M4 | Requests recorded before 2026-11-19 (no `mode`) | Listed in **no** mode (strict reading of the request). They stay readable from the journal of their pass (`get_many`, the journal being already per mode) and are purged after 30 days unless journaled. |
| M5 | Recent Activity | Emptied when the Dashboard sees `test_mode` change. |
| M6 | Mode before cycle | Home's opening dialog asks the mode, then the cycle (and the pass choice); the page keeps that order at its top. |

## 4. Lots

1. **Journal** (done): `CheckpointStore.cycles()` and `journal()` read the current mode's store only.
   Tests: `test_cycles_lists_months_with_the_passes_of_the_current_mode_only`,
   `test_the_test_journal_stays_in_redis_and_each_mode_reads_only_its_own`.
2. **Tracking** (done): `RequestTracker.list_recent(mode=)`, `TrackingService` (gate injected), middleware `mode`,
   WebSocket `has_job` check. Tests in `test_request_tracker.py`, `test_tracking_service.py`,
   `test_request_tracking_middleware.py`, `test_etl_logs_ws.py`, `test_checkpoint_store.py`
   (`test_a_mode_knows_only_the_jobs_its_own_pipeline_launched`).
3. **etlui** (done): mode first on Home, Recent Activity emptied on a switch (`Dashboard.vue`).
4. **`input/` and `output/` per mode**: proposed below, waiting for the owner.

## 5. Lot 4: proposal (not implemented)

Read from the code on 2026-11-19, nothing run.

- Three ETL scripts write to `os.getcwd()/input` with no parameter: `etl/scripts/fetch_pridec_climate.py:38,57`,
  `fetch_pridec_disease.py:52,65`, `fetch_pridec_geojson.py:45,60`. `etl/` must not be changed, and changing the
  worker's cwd would also move `logs/`, `logs/etlhub.db`, `data_dir` and the GEE key lookup. So explicit per-mode
  paths in etlhub alone (about 7 places) would still leave these three files in the shared `./input`.
- **Option A (smallest)**: `<root>/input` and `<root>/output` become symlinks to `work/production/{input,output}` or
  `work/test/{input,output}`, re-pointed atomically (`os.replace` of a temporary link) by `set_mode` (after the lock
  check and the test pass's pause) and at API start from `test_mode_enabled()`. Nothing else changes: uploads,
  pass folders, the archive, the report, the forecast mount and the `fetch_*` scripts follow the link.
- To check before choosing A:
  - that `dockerd` follows a symlinked bind-mount source (`forecast_runner.py:73-74`), one manual `docker run`;
  - the worker's real cwd in deployment, and that `DATA_DIR`, `LOGS_DIR`, `HOST_PWD` are not overridden;
  - the root `.gitignore` (`input/` matches directories only: the links need `/input`, `/output`);
  - the CLI (`compose.yaml`, `pridec`) would follow the current mode too: a change of behaviour;
  - migration: test pass folders already under `input/<cycle>/<pass>/` must be moved by pass id (ids in the Redis
    blob), or resuming an old test pass restores nothing; origin of the existing `output/dry_run/` unknown.
- Option B (explicit per-mode root, the old `_uploads_dir` pattern) needs the same plus moving the `fetch_*` outputs
  after each job; larger and only partly separate.

## 5b. Re-check with a mode per user (2026-11-19, later the same day)

Owner: each user chooses their mode without changing the server's; a request carries the parameters of its mode.
Checked in the code (nothing run):

- **Option A is ruled out** [Certain]: a symlink is one global state; two users in different modes, or a job of
  one mode while a user of the other uploads, cannot both be served.
- **Option B becomes the only way**, and per-request mode is cheap to carry: every mode read goes through
  `CheckpointStore._test_mode` (`checkpoint_store.py:290`, read at 311, 654, 939, 1130, 1141, 1177), which can read a
  ContextVar like `core/job_context.job_dry_run`; the session (`auth_store.create_session`, JSON in Redis) can hold
  the user's mode and `get_current_user` already fills `request_context`; Celery tasks get it in their kwargs like
  `dry_run` (`tasks.py:89`). The browser's WebSocket and `<a download>` links send the session cookie, not headers.
- Places with explicit paths etlhub can make per mode: `dependencies.py:103` (uploads), `checkpoint_store.py:302`
  (pass folders, clear, keep), `forecast_report_router.py:30,60`, `forecast_runner.py:73-74,80` (host side of the
  mount only; the container keeps `/app/input`, `/app/output`), `validation_use_cases.py:33` (takes `input_dir`),
  `post_forecast.py:21,30` (relative `output/`, etlhub's own copy).
- **New with a mode per user: two jobs can run at once.** `pipeline_lock` is a table of each store
  (`checkpoint_store.py:49`), so today's "one job at a time" was only true because one mode was active. Then:
  - `fetch_climate|disease|geojson` write `os.getcwd()/input/<fixed name>` (`etl/scripts/fetch_pridec_*.py`), shared;
  - the run context `DISEASE_CODE` / `OU_LEVEL` is written to the global Redis config at each run job
    (`apply_to_config_store`, `checkpoint_store.py:228`) and read by `fetch_disease` and the forecast's env file
    (`forecast_runner.py:38`): two runs would overwrite each other's; per job instead through `script_config._get`
    (as `DRYRUN`), in etlhub only;
  - `post_forecast` / `update_key` redirect the API's process-wide stdout: two at once mix their logs.
- Options for the `fetch_*` files: B1 per-task `chdir` in the Celery child (prefork by default, `run_celery.py` sets
  no pool; needs absolute `logs_dir`, `data_dir`, `host_pwd`; breaks with a thread or solo pool); B2 one lock for
  both modes (jobs serialized server-wide) and move the three files into the mode's folder after the job; B3 an
  input-folder setting in the three scripts (changes `etl/`, owner's approval needed).
- Not verified: the deployed worker's pool, concurrency and cwd; Docker on a symlinked bind source (moot now).

## 5c. Owner's decisions on the mode per user (2026-11-19)

| # | Question | Decision |
|---|---|---|
| U1 | Where the user's mode lives | Server side, in the session (`session:{hash}` JSON in Redis). `PUT /pipeline/mode` changes the caller's session only. |
| U2 | Concurrency | One job at a time on the whole server, both modes together. Each mode may keep its own active pass. |
| U3 | Folders | Production keeps `./input` and `./output` (CLI `pridec`, `compose.yaml` unchanged); test gets `test/input` and `test/output`. Old test pass folders moved by pass id. |
| U4 | `fetch_*` files (`etl/` untouched) | B2: before a test-mode fetch, etlhub sets aside the production files the script overwrites in `./input`, runs it, moves its output to `test/input`, puts the production files back. Safe only because of U2 (`ponytail:` limit). |
| U5 | Mode right after login | Test. |

Implementation plan (done, § 7): the global lock row in the production SQLite file for both modes (a test-mode
transaction also opens the file one; a production transaction never takes the test blob's Redis lock: no deadlock);
the store reads the mode from the request (session) or the job (Celery kwargs, like `dry_run`), defaulting to test;
the log WebSocket reads it from the session; the per-mode folders in the places of § 5b.

Consequences, confirmed by the owner:
- switching one's own mode no longer pauses the other mode's active pass, is no longer refused while a job runs, and
  is no longer a `mode_changed` journal event (it changes nothing shared);
- a job of the other mode holding the lock shows as "a job of the other mode is running", without its task or id;
  "Release the lock" stays possible from either mode (a killed worker must not block both modes).

## 7. As implemented (2026-11-19)

- `core/job_context.py`: `pipeline_test_mode` (ContextVar), `current_test_mode()` (test outside a session or job),
  `work_dir(root, name, test_mode)`.
- Session: `auth_store.create_session` (`test_mode: true`), `set_session_mode` (keeps the expiry);
  `get_current_user` sets the ContextVar and `request_context["mode"]` (the request log's); `PUT /pipeline/mode` →
  the session, 401 when it is gone. The Redis key `pipeline:test_mode` and `PipelineGate.set_mode` are gone; no more
  `mode_changed` events (old ones stay in the journals).
- Celery: `CeleryTaskLauncher.launch` adds `test_mode` to the task kwargs; `_run_task` serves the job in it (store,
  folders, `finish`). A task queued before this version has none: served in test.
- Store: `_transaction` by the mode served; test transactions `ATTACH` the file as `shared` and `BEGIN IMMEDIATE`
  (the lock row is the file's); `_lock`, `held_lock`, `_check_lock_free` name only a job of the mode served;
  `release_lock` works from either mode and journals in the job's. `_input_dir`, `_output_dir` follow the mode; an old
  test pass folder in `./input`, `./output` moves to `test/` on first use (`ponytail:`).
- Paths: uploads (`dependencies.py`), report and archive, forecast mounts, validation, `post_forecast`.
- B2: `etl_use_cases._into_mode_folder` (`ponytail:`, see its docstring).
- etlui: `ModeToggle` enabled while a job runs; the lock of the other mode shown without id.
- Tests: etlhub 330, etlui 150; end to end `e2e/test_mode_isolation.py` (headless, 2026-11-19 on the local stack: 9 passed, the forecast xfail because `forecast_start` = the cycle goes past the test data). Not verified: a real Celery worker receiving `test_mode`, Docker mounting
  `test/input`, the `ATTACH` of a WAL file under real concurrency, the migration of real old test passes.

## 8. Leaving a mode mid-pass (owner's rule, 2026-11-19)

A pass lives in one mode (its store), never two. A user who switches mode while the mode left has an **active** pass
must choose what becomes of it: `PUT /pipeline/mode` answers 409 `confirmation_required`, `impact` `{pass_id, cycle,
mode, to, actions: ["pause", "abandon"]}`, and does nothing until resent with `pass_action`. The pass is then paused
(resumed later in its mode) or abandoned, journaled with `detail` `{cause: "mode_change", reason: "Mode changed
manually by the user: from <mode> to <other>"}` and the user as actor. Refused while a job runs (as pause and abandon).
The same mode again, or no active pass: nothing asked. A paused pass is not touched.

This replaces the first point of the consequences of § 5c ("no longer pauses"): the switch still never touches the
other mode, but it now ends the user's own active pass. Other users of that mode see their shared pass paused or
abandoned. etlui: `ImpactDialog` shows one button per `impact.actions` ("Pause the pass", "Abandon the pass").
`CheckpointStore.leave_mode`, `PipelineGate.leave_mode`; tests `test_leaving_a_mode_*`,
`test_the_pass_left_by_a_mode_change_says_so_in_its_journal`, `test_switching_mode_mid_pass_asks_first_*`.

Confirmed by the owner (2026-11-19):
- switching mode while a job runs, when the mode left has an active pass, stays refused until the job ends (pause and
  abandon need the lock free, and the lock is both modes');
- the pass is shared by the users of its mode: one user's switch pauses or abandons it for all of them;
- B2 (`_into_mode_folder`) is kept for the `fetch_*` files.

## 6. Limits

- Two users of the same mode share its passes, as before.
- `mode_changed` events stay in the journal of the mode that was left: they say a switch happened, not what was
  done in the other mode.
- `GET /api/tracking/requests` lists at most `limit` requests of the mode, after filtering (SQL), so a mode is not
  starved by the other's requests.
