# Pipeline tracking: quick guide

This guide briefly explains how etlhub tracks and controls the monthly pipeline (target design, revised 2026-10-12).
- The workflow itself (3 phases, `pridec` commands, order) follows the reference documentation (`pivot_forecast.sh`), which is authoritative.
- The full design, and what is already implemented, are in [pipeline-checkpoints.md](pipeline-checkpoints.md).
- The diagrams are in [pipeline-checkpoints-diagrams.md](pipeline-checkpoints-diagrams.md).

> The code applies this revision, except `calc_orgunit_alerts` (still 501), the test-mode scope and the level check
> of `external_data`: see the status at the top of [pipeline-checkpoints.md](pipeline-checkpoints.md).

## In one sentence

etlhub records, for each month, what **really succeeded**. It **refuses** anything out of the planned order,
runs **only one job at a time**, handles **only one forecast (source × disease) at a time**, and asks for a
**confirmation** before undoing what was validated.

## The cycle

A **cycle** is the full run of the pipeline, **once a month**. It is named after the current month (`YYYYMM`).
- It opens at the first launch of the month.
- When the **month changes**, a new cycle starts automatically: the old one stays unfinished if it was not finished,
  and its open run is abandoned.
- Once the 3 steps are valid, it is **closed**: the month cannot run a second time.

| # | Step | What must succeed | Order |
|---|---|---|---|
| ① | `data_import` (5 items) | `import_gee`, `import_pivot_com`, `import_pivot_csb`, the `approve_imports` decision, then `build_analytics` | Imports in any order; `approve_imports` after the 2 pivot imports; `build_analytics` last |
| ② | `forecast` (71 items) | **9 runs**, one per source × disease pair (ADJ, COM, CSB × Malaria, Diarrhea, Respinf) | Runs in any order, only one open at a time |
| ③ | `system_update` (2 items) | `build_analytics` → `update_key` | Fixed |

- **`approve_imports`** is a human decision: check that COM cases are < 100 and CSB cases < a limit (not set yet).
- **`build_analytics`** must go through the etlhub API. Launched from the DHIS2 interface, etlhub does not see it and step ① stays invalid.

### A forecast run

Open it with `POST /pipeline/runs` `{"source": "CSB", "disease": "Malaria"}`. Opening **empties `input/` and `output/`**,
copies back the files already uploaded and sets the run context:

| Pair | `DISEASE_CODE` | `OU_LEVEL` | `ALERT_NAME` |
|---|---|---|---|
| ADJ/x | `pridec_historic_ADJ<x>` | 6 | — |
| COM/x | `pridec_historic_COM<x>` | 6 | — |
| CSB/x | `pridec_historic_CSB<x>` | 5 | `CSB<x>Vigilance` |

This context is rewritten into the dynamic config at each job of the run: there is nothing to change in the Admin page.

Items of a run, with their prerequisites:

```
config/<disease>      ┐  (upload, one per disease)
external_data/<level> │  (upload, one per level)
fetch_disease         ├─→ validate_inputs ─→ forecast ─→ [calc_orgunit_alerts, CSB only] ─→ approve ─→ post_forecast
fetch_climate         │
fetch_geojson         ┘
```

- **`config.json`: mandatory, one per disease.** Upload it from the interface in the first run of the disease;
  it is copied back into `input/` automatically for its 2 other runs. That makes 3 uploads per cycle. The server writes
  `forecast_start` into it, as `jq` does in `pivot_forecast.sh`. The interface shows the expected file:
  `config_malaria.json`, `config_diarrhea.json`, `config_respiratory.json` (for `Respinf`).
- **`external_data.csv`: mandatory, one per level** (`external_data/fkt` for ADJ and COM, `external_data/csb` for CSB).
  Same principle: 2 uploads per cycle. A file that does not match the run's level is refused (422).
- The files in the repository's `forecast_assets/` serve as templates.
- Replacing a file **already used** needs `confirm=true` and resets **only the open run**; the runs already
  computed with the old file keep their `success` and are listed in `impact.stale_runs`.
- `calc_orgunit_alerts` (CSB) computes the alert thresholds with `ALERT_NAME` (command `pridec etl calc_orgUnit_alerts`).
- `approve` is a decision: `POST /pipeline/runs/current/approve` with `{"decision": "approve"}`, or `"reject"` to
  redo the forecast.
- The run **closes** when `post_forecast` succeeds; its `forecast_report.html` is then kept
  (`GET /pipeline/runs/{source}/{disease}/report`), since the next run empties `output/`. It can also be **abandoned** (`DELETE /pipeline/runs/current`, administrators only):
  nothing is published, and its items go back to `pending`.

## The rules

| Rule | Content |
|---|---|
| R1 | Every item is mandatory (`config.json`: one item per disease; `external_data.csv`: one item per level). |
| R2 | An item starts only if its prerequisites are in `success`. |
| R3 | Only one job at a time. **The lock never expires.** |
| R4 | A step only counts if the previous one counts. Otherwise the following ones are blocked, but their `success` statuses are kept. |
| R5 | Undoing what was validated needs `confirm=true`: relaunching a `success`, replacing a file already used, reopening a closed pair. |
| R6 | Only one forecast run open at a time. |

A refusal answers **409** (422 for an `external_data.csv` that does not match the run's level) and writes nothing.
All messages are in English:

```json
{"message": "build_analytics needs data_import/import_gee in success first"}
{"message": "fetch_climate needs an open forecast run (POST /pipeline/runs)"}
{"message": "Run CSB/Malaria is open: finish or abandon it first"}
{"message": "import_gee (import_gee_ab12cd34) is running since 2026-10-09T14:02:11: one job at a time"}
{"message": "Cycle 202610 is complete: the next cycle starts next month"}
```

## Item statuses

| Status | Meaning |
|---|---|
| `pending` | never launched, or reset (no row in the database) |
| `running` | launched, not finished yet |
| `success` | succeeded: counts to validate the step |
| `error` | failed: relaunches without confirmation |

**In a run**, relaunching or replacing an item resets **everything that depends on it** in the run to `pending`.
For example, relaunching `fetch_climate` resets `validate_inputs` and `forecast` to `pending`.

## Confirmation (R5)

Without `confirm=true`, the server describes the impact instead of acting:

```json
{
  "code": "confirmation_required",
  "message": "COM/Respinf:fetch_climate is already in success: resend with confirm=true to relaunch it",
  "impact": {
    "item": "COM/Respinf:fetch_climate",
    "step": "forecast",
    "current_step": "forecast",
    "reset_items": ["COM/Respinf:validate_inputs", "COM/Respinf:forecast"],
    "blocked_steps": ["system_update"],
    "kept_items": {"system_update": 0}
  }
}
```

etlui shows this impact, asks for approval, then resends the same request with `?confirm=true`.
The parameter exists on every launch route, on `POST` and `DELETE /input/files/{name}` and on `POST /pipeline/runs`.

## Test mode

The etlui **"Test mode" (test = YES)** button switches etlhub to test mode.
- Switch with `PUT /pipeline/mode` `{"dry_run": true | false}`.
- This mode passes `DRYRUN=True` to `import_gee` (quick partial import) and to `post_forecast` (no write to PRIDE-C).
  Not to be confused with the `DRYRUN` option of each `pridec` command, whose effect varies from one command to another.
- In test mode, checkpoints, runs and the lock are kept **in Redis only**, never in `logs/etlhub.db`.
  Production data is neither visible nor changed. The cycle stays the real month; the same rules apply.
- **Going back to production** (`dry_run: false`) erases what is in Redis. If there is test data,
  `confirm=true` is needed (otherwise 409 `confirmation_required`, with the open run and the successful items in `impact`).
- Switching is refused while a job runs.
- `GET /pipeline/checkpoints` shows the mode (`dry_run`).

## Tracking endpoints

| Method | Route | Role |
|---|---|---|
| GET | `/pipeline/checkpoints?cycle=YYYYMM` | State of the cycle: `current_step`, `cycle_state`, `run`, `lock`, steps (`done`, `accessible`) and items (`status`, `launchable`) |
| POST | `/pipeline/runs` | Opens the run of a pair |
| DELETE | `/pipeline/runs/current` | Abandons the open run (administrators only) |
| GET | `/pipeline/runs/{source}/{disease}/report` | Report of a closed run, kept when it closed (404 if none) |
| POST | `/pipeline/runs/current/approve` | `{"decision": "approve" \| "reject"}` |
| POST | `/pipeline/imports/approve` | `{"decision": "approve" \| "reject"}`: the `approve_imports` decision of step ① |
| PUT | `/pipeline/mode` | `{"dry_run": true \| false}`: test or production mode (`confirm=true` to leave test mode with data) |
| DELETE | `/pipeline/lock` | Frees the lock of a job whose worker was killed; the `running` item becomes `error` (administrators only) |
| POST | `/calc_orgunit_alerts` | Job of the CSB runs, between `forecast` and `approve` (501 today: no script) |

All these routes require an etlui session.

## Known limits

- **A killed worker blocks everything** until `DELETE /pipeline/lock`.
- **A cycle not finished by the end of the month stays unfinished**: the next month starts from zero.
- **`build_analytics` launched outside etlhub** (DHIS2 interface) is not seen: step ① stays invalid.
- `DELETE /output/reset` and jobs launched from the command line (`./pridec`) bypass these controls.
- **etlui** is connected (2026-10-09), but has only been checked with a mocked API. The etlui dashboard no longer has a "reset output" button (`DELETE /output/reset` is still available in the API).
- Still open (value of `forecast_start`, CSB limit, `calc_orgunit_alerts` Celery or synchronous, columns
  that distinguish fkt and csb, test config): see the end of [pipeline-checkpoints-diagrams.md](pipeline-checkpoints-diagrams.md).

## Where the code is

| File | Content |
|---|---|
| `domain/pipeline.py` | Steps, items, prerequisites, rules (pure code, no I/O) |
| `infrastructure/checkpoint_store.py` | Tables `checkpoints`, `pipeline_lock`, `forecast_runs` (`logs/etlhub.db`), run context, emptying of `input/` and `output/` |
| `api/routers/pipeline_router.py` | Tracking and run routes |
| `infrastructure/tasks.py` | Lock taken at launch, result at the end of the job |
| `tests/infrastructure/test_checkpoint_store.py`, `tests/api/test_pipeline_router.py` | Tests |

**Adding a new job type?** Add it in `domain/pipeline.py`: in `PIPELINE`, and in `RUN_TASKS` if it
belongs to a run. Otherwise its launch fails.
