# Pipeline checkpoints: the essentials

etlhub records what **really succeeded** in the month's pipeline, and **refuses** what breaks the rules
(design revised on 2026-10-12, applied except `calc_orgunit_alerts`, the test-mode scope and the `external_data` check;
the system-configuration changes below are requested for the next version).
The workflow itself follows the reference documentation (`pivot_forecast.sh`), which is authoritative.
More detail: [guide](pipeline-checkpoints-guide.md) · [diagrams](pipeline-checkpoints-diagrams.md) · [design](pipeline-checkpoints.md).

## The system

An etlhub is paired with one DHIS2 instance, called a **system**. An admin sets the system's defaults:
- which `import_*` steps of `data_import` are required;
- which `dataElement` items can be forecast, and which of them must be forecast to complete the cycle;
- for each `dataElement`: a default `config.json`, an optional default `external_data.csv`, `OU_LEVEL` and `ALERT_NAME`.

The smallest unit of forecast is the **`dataElement`** (named `pridec_historic_<x>`); only one is handled at a time.

## The cycle

- **1 cycle = the whole pipeline, once a month**, named after the month (e.g. `202610`).
- It **opens** at the first launch of the month.
- When the **month changes**, a new cycle starts on its own. The old one, if not finished, stays unfinished
  (it is kept in the history) and its open run is abandoned.
- Another month can be chosen from etlui (month input next to "Cycle", `PUT /pipeline/cycle`): launches then go to it until it is set back to the current month. Not while a job runs or a run is open; never a future month.
- It **closes** when the 3 steps are valid: the PRIDE-C application is up to date. An admin can reopen any step as needed.

## The 3 steps

| Step | To succeed | Order |
|---|---|---|
| ① `data_import` | The `import_*` steps required by the system (Pivot: `import_gee`, `import_pivot_com`, `import_pivot_csb`; the `import_pivot_*` ones are optional and set by an admin), the `approve_imports` decision (COM cases < 100, CSB cases < 1000; the user can override by approving), then `build_analytics` | Imports in any order, `approve_imports` after the pivot imports, `build_analytics` last |
| ② `forecast` | **One run per `dataElement`** that the system requires (number set by an admin). Pivot: **9 runs**, ADJ, COM, CSB × Malaria, Diarrhea, Respinf | Runs in any order, **only one open at a time** |
| ③ `system_update` | `build_analytics` → `update_key` | Fixed |

`build_analytics` must go through the etlhub API: launched from DHIS2, it is not seen and step ① stays invalid.

## A forecast run (step ②)

1. **Open** the run of a `dataElement` (`POST /pipeline/runs`). The server empties `input/` and `output/`, copies back the files
   already uploaded, then sets `DISEASE_CODE`, `OU_LEVEL` and `ALERT_NAME` on its own, from the system configuration
   (Pivot: `OU_LEVEL` 6 for ADJ/COM, 5 for CSB; `ALERT_NAME` for CSB only).
2. **Files**, from the user interface:
   - `config.json`: **mandatory, 1 per run**. The `dataElement` default is used, or the user uploads another one.
     The server writes `forecast_start` into it: by default the current month (`YYYYMM`), **editable by the user**.
   - `external_data.csv`: **optional, 1 per run**. An admin can set a default per `dataElement`; `dataElement`s can share the same file.
     `validate_inputs` checks that its `orgUnit` values match those of `disease_data.json` (no level check).
   - The files in `forecast_assets/` serve as the defaults.
3. **Jobs**: `fetch_disease`, `fetch_climate`, `fetch_geojson` → `validate_inputs` → `forecast`
   → `calc_orgunit_alerts` (optional, only if the admin sets an `ALERT_NAME`; synchronous, reads `output/`, publishes an alert `dataElement` to PRIDE-C).
4. **Decide**: read the report, then `approve` (or `reject` to redo the forecast).
5. **Publish**: `post_forecast`. The run **closes** (its report is kept: `GET /pipeline/runs/{source}/{disease}/report`) and another pair can be opened.

A run can be **abandoned** at any time, by an administrator: nothing is published, and its steps start again from zero.

## The rules

| | Rule | If it is not respected |
|---|---|---|
| **R1** | Every run requires a `config.json` (`external_data.csv` is optional). | The step is not validated. |
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
- Test mode still acts on every script (global `DRYRUN`); decided: it should use `forecast_assets/test_config.json` (Ranger + Naive) for `forecast`. The `external_data.csv` check (`orgUnit` match in `validate_inputs`) is not implemented yet.
- **Interface** (etlui): connected since 2026-10-09; it has not been tested against a real etlhub, only with a mocked API. The etlui dashboard no longer has a "reset output" button (`DELETE /output/reset` is still available in the API).
- A cycle not finished by the end of the month stays unfinished: nothing finishes it for you.
- `DELETE /output/reset` and the command line (`./pridec`) bypass these controls.
- Open points are answered ([diagrams](pipeline-checkpoints-diagrams.md#open-points)): `forecast_start` defaults to the current month and is editable,
  CSB limit is 1000 cases, `calc_orgunit_alerts` is synchronous, test mode uses `test_config.json`, no level check on `external_data`.

## Planned changes (next version)

- `external_data.csv` becomes optional; an admin can give a default per `dataElement`.
- `forecast_start` is written by the server by default but editable by the user.
- The forecast unit becomes the `dataElement` (`pridec_historic_<x>`), each linked by an admin configuration to a default `config.json` that an upload can overwrite.
- Admin-configurable pipeline (steps, `dataElement`s, defaults), versioned in the database: proposal in [pipeline-config.md](pipeline-config.md).
