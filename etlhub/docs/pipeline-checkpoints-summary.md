# Pipeline checkpoints: the essentials

etlhub records what **really succeeded** in the month's pipeline, and **refuses** what breaks the rules
(design revised on 2026-10-12, applied except `calc_orgunit_alerts`, the test-mode scope and the level check of `external_data`).
The workflow itself follows the reference documentation (`pivot_forecast.sh`), which is authoritative.
More detail: [guide](pipeline-checkpoints-guide.md) · [diagrams](pipeline-checkpoints-diagrams.md) · [design](pipeline-checkpoints.md).

## The cycle

- **1 cycle = the whole pipeline, once a month**, named after the month (e.g. `202610`).
- It **opens** at the first launch of the month.
- When the **month changes**, a new cycle starts on its own. The old one, if not finished, stays unfinished
  (it is kept in the history) and its open run is abandoned.
- It **closes** when the 3 steps are valid: the PRIDE-C application is up to date. The same month cannot run twice.

## The 3 steps

| Step | To succeed | Order |
|---|---|---|
| ① `data_import` | `import_gee`, `import_pivot_com`, `import_pivot_csb`, the `approve_imports` decision (COM cases < 100, CSB cases < limit), then `build_analytics` | Imports in any order, `approve_imports` after the pivot imports, `build_analytics` last |
| ② `forecast` | **9 runs**: ADJ, COM, CSB × Malaria, Diarrhea, Respinf | Runs in any order, **only one open at a time** |
| ③ `system_update` | `build_analytics` → `update_key` | Fixed |

`build_analytics` must go through the etlhub API: launched from DHIS2, it is not seen and step ① stays invalid.

## A forecast run (step ②)

1. **Open** the run of a pair (`POST /pipeline/runs`). The server empties `input/` and `output/`, copies back the files
   already uploaded, then sets `DISEASE_CODE`, `OU_LEVEL` (6 for ADJ/COM, 5 for CSB) and `ALERT_NAME` (CSB) on its own.
2. **Files**, from the user interface, **all mandatory**:
   - `config.json`: **1 per disease** (`config_malaria.json`, `config_diarrhea.json`, `config_respiratory.json`).
     Uploaded in the first run of the disease; the 2 other runs get it automatically.
     The server writes `forecast_start` into it.
   - `external_data.csv`: **1 per level** (fokontany or CSB), same principle. A file of the wrong level is refused (422).
   - The files in `forecast_assets/` serve as templates.
3. **Jobs**: `fetch_disease`, `fetch_climate`, `fetch_geojson` → `validate_inputs` → `forecast`
   → `calc_orgunit_alerts` (CSB only).
4. **Decide**: read the report, then `approve` (or `reject` to redo the forecast).
5. **Publish**: `post_forecast`. The run **closes** (its report is kept: `GET /pipeline/runs/{source}/{disease}/report`) and another pair can be opened.

A run can be **abandoned** at any time, by an administrator: nothing is published, and its steps start again from zero.

## The rules

| | Rule | If it is not respected |
|---|---|---|
| **R1** | Everything is mandatory, `external_data.csv` included. | The step is not validated. |
| **R2** | An action waits for its prerequisites to succeed. | 409 refusal. |
| **R3** | **Only one job at a time.** The lock **never expires**. | 409 refusal. Crashed worker: `DELETE /pipeline/lock` (administrators: DHIS2 authority `ALL`). |
| **R4** | A step only counts if the previous one counts. | Following steps blocked; their successes are kept and count again later. |
| **R5** | **Undoing a success needs a confirmation**: relaunching a successful action, replacing a file already used, reopening a finished run. | 409 `confirmation_required` refusal describing the impact; resend with `?confirm=true`. |
| **R6** | **Only one forecast run open at a time.** | 409 refusal. |

Good to know:
- A refusal **never writes anything**. Messages are in English.
- Relaunching an action **in error** needs no confirmation.
- In a run, relaunching or replacing something **resets everything that depends on it in that run**.
  Other runs are not touched.

## Test mode

The etlui **"Test mode" (test = YES)** button switches etlhub to test mode (`PUT /pipeline/mode` `{"dry_run": true | false}`).
- This mode passes `DRYRUN=True` to `import_gee` (quick partial import) and to `post_forecast` (nothing is written to PRIDE-C).
  Not to be confused with the `DRYRUN` option of each `pridec` command, whose effect varies by command.
- In test mode, checkpoints, runs and the lock are kept **in Redis only**, never in `logs/etlhub.db`.
  Production data is neither visible nor changed. The cycle stays the real month; the same rules apply.
- **Going back to production** (`dry_run: false`) erases what is in Redis. If there is test data,
  `confirm=true` is needed (otherwise 409 `confirmation_required`, with the open run and the successful items in `impact`).
- Switching is refused while a job runs.
- `GET /pipeline/checkpoints` shows the mode (`dry_run`).

## Statuses

`pending` (not done) · `running` (in progress) · `success` (succeeded, counts) · `error` (failed, to relaunch)

## Where am I?

`GET /pipeline/checkpoints` returns:
- the current step, the open run and the running job;
- for each step: `done` (validated) and `accessible` (work can be done in it);
- for each action: `status` and `launchable` (can be launched now).

## Current limits

- **`calc_orgunit_alerts` still answers 501** (no script): CSB runs, and so the cycle, cannot complete.
- Test mode still acts on every script (global `DRYRUN`), and the level of `external_data.csv` is not checked yet.
- **Interface** (etlui): connected since 2026-10-09; it has not been tested against a real etlhub, only with a mocked API. The etlui dashboard no longer has a "reset output" button (`DELETE /output/reset` is still available in the API).
- A cycle not finished by the end of the month stays unfinished: nothing finishes it for you.
- `DELETE /output/reset` and the command line (`./pridec`) bypass these controls.
- Open points: value of `forecast_start`, CSB limit of `approve_imports`, nature of `calc_orgunit_alerts`,
  columns that distinguish fkt and csb, test-mode config ([diagrams](pipeline-checkpoints-diagrams.md#open-points)).
