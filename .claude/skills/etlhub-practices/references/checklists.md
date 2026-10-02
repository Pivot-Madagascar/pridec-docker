# Checklists

Tick every line or say why it does not apply.

## A. New ETL job type

- [ ] Script function exists in `etl/scripts/` and is imported at the top of `etl_use_cases.py`
- [ ] Service method generates `f"{type}_{uuid.uuid4().hex[:8]}"` and calls `task_launcher.launch(...)` (templates.md §1)
- [ ] `run_<name>` wrapper goes through `_execute_etl_job` (§2)
- [ ] `task_<name>` uses `_run_task`, no hand-written body (§3)
- [ ] Entry added to `CeleryTaskLauncher._registry` (§3)
- [ ] Router: 202, `ETLResponse`, `summary`, `description`, `response_description`, `webhook_url` (§4)
- [ ] Router is protected (see m1) once m1 has been merged
- [ ] Router test: 202, `status == "accepted"`, `job_id` present (§7)
- [ ] Task test: success and failure, failure re-raises (§8)
- [ ] No blocking call in the handler, no new `print(`, no `except Exception: pass`
- [ ] Endpoint table in `.claude/skills/etlhub/references/reference.md` updated
- [ ] `etlui` told about the new endpoint if it will call it

## B. Contract change (response shape, job_id, WebSocket, webhook payload, close code)

- [ ] Listed every field that changes and who reads it (`etlui/src/composables/useEtlPipeline.ts`, `useWebSocketLogger.ts`, `views/JobStatus.vue`, external webhook receivers)
- [ ] `etlui` updated **in the same change**
- [ ] `ETLResponse` / `JobStatus` / WebSocket message names kept, or the user explicitly agreed to rename
- [ ] Tests updated; contract-level assertions kept (`status`, `job_id`)
- [ ] User warned if the change is breaking for non-`etlui` callers

## C. Change to `tasks.py`, `job_store.py`, `forecast_runner.py` or `etl_use_cases.py`

- [ ] Re-raise after the "error" status is preserved
- [ ] `_update_task_status` still merges (`started` and `logs` not overwritten)
- [ ] No new silent `except … pass`; failures logged with the job id
- [ ] Redis keys, TTL (24 h) and channels (`etl_logs:{id}`, `etl_status:{id}`) unchanged
- [ ] Test added (these modules are mostly untested)
- [ ] For forecast: `HOST_PWD` is a host path, volumes `input` ro and `output` rw unchanged, temp env file still removed

## D. PR review

Blockers:
- [ ] Real endpoint called against real DHIS2 or the host, or a secret printed
- [ ] New unauthenticated endpoint that writes (DHIS2, files, Docker)
- [ ] Blocking work inside an `async def` handler
- [ ] New import direction violation (`application`/`infrastructure` → `api`)
- [ ] Frozen contract changed without `etlui` change
- [ ] New `webhook_url` use without validation

Should fix:
- [ ] `print(` in `etlhub/` outside job output; module without a logger that can fail
- [ ] Test asserts nothing about behaviour (Redis is a `MagicMock`, so "passes" proves little)
- [ ] Patch applied to a name already imported elsewhere (no effect)
- [ ] Dead code added (`JWT_SECRET`, `WebhookNotification`, `ValidationResponse` are existing examples: do not add more)
- [ ] `.env.example` / docs not updated for a new variable (`LOGS_DIR`, `DATA_DIR`, `HOST_PWD`, `ENV_FILE` are currently missing)

## E. Before saying "done"

- [ ] `cd etlhub && ../test-venv/bin/python -m pytest tests -m "not integration"` run, result reported (baseline: 29 pass, 1 known failure until m6, 1 deselected)
- [ ] Only the files intended are changed (`git status --short`)
- [ ] New or changed behaviour has a test in the same commit, asserting body or stored state and not only `status_code`
- [ ] Coverage of the touched files is not below the baseline (`etlhub/docs/DEVELOPMENT.md` §3; keep `COVERAGE_FILE` outside the repository)
- [ ] You said whether the test was written first or after; do not claim TDD without evidence
- [ ] Anything you could not verify is said explicitly