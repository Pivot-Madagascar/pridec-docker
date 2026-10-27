# Pass folders and a new pass after a pause

> **Status: implemented on 2026-10-27** (etlhub and etlui). Supersedes, in
> [../cycle-passes/cycle-passes.md](../cycle-passes/cycle-passes.md), the refusal of a launch on a month whose last pass
> is paused (§ 12 "Differences"), the kept files in `uploads/<cycle>/<pass>/` and the reset of the open run on resume.

## 1. What is asked

1. Pausing, abandoning or completing the current pass lets the user start a **new pass in the same cycle**. A month
   can then have several `paused` and `abandoned` passes.
2. Each pass that is not abandoned has its folders `input/<cycle>/<pass>/` and `output/<cycle>/<pass>/`, created when
   the pass starts.

## 2. Decisions (owner, 2026-10-27)

| # | Question | Decision |
|---|---|---|
| F1 | How do the ETL scripts (`etl/`, not modified) use the pass folders? | `input/` and `output/` stay the **working folders**. Their files are copied into the pass folders at pause, and copied back on resume |
| F2 | One folder per pass or per run? | **Per pass.** Opening a run still empties the working files of the previous run of the pass |
| F3 | Abandoned pass | Its folders are deleted at the abandon, **except the reports** of its closed runs (`output/<cycle>/<pass>/report_*.html`) |
| F4 | Complete pass | Its folders are kept |
| F5 | When does a pass start? | ~~At the first launch of a `data_import` job~~. **Revised the same day**: at the click on Start with "New pass" (Home), `POST /pipeline/passes` (§ 6). A first launch still starts one when none is active (direct API calls) |
| F6 | New pass while the last pass of the month is paused | 409 `confirmation_required`, impact `{cycle, paused_pass}`, the message names the paused pass, which stays paused |
| F7 | `config.json` / `external_data.csv` of the new pass | Copied from the **previous pass of the cycle**, only when it is `paused` or `complete`. They are carried as `success` (`carried_over` event, like the imports). After an abandon, nothing is copied |
| F8 | `uploads/` mechanism | Removed: the uploads are kept in `input/<cycle>/<pass>/` |
| F9 | Existing files | Moved once to the pass folders. The working files of `input/` and `output/` are copied into the last paused pass when no pass is active |
| F10 | Test and production share `input/` and `output/` | **Known limit**: a production pass left active while a test pass starts loses its working files (its run fetches again) |

## 3. Layout

```
input/                      working files of the active pass (what the scripts read and write)
input/<cycle>/<pass>/       config_<disease>.json, external_data_<fkt|csb>.csv (kept)
                            + a copy of the working files of input/ (pause, complete)
output/                     working files of the active pass
output/<cycle>/<pass>/      report_<source>_<disease>.html (kept, one per closed run)
                            + a copy of the working files of output/ (pause, complete)
```

A 6-digit folder in `input/` or `output/` is a cycle: it is never emptied as a working file, and `GET /output/archive`
leaves it out.

## 4. Life of the files

| Event | Files |
|---|---|
| Pass starts (first launch) | working files emptied (the previous pass saved them or dropped them), pass folders created, config / external_data copied from the previous pass if it is paused or complete (F7) |
| Upload | written in `input/`, kept in `input/<cycle>/<pass>/` |
| Run opens | working files emptied, the kept config of its disease and external_data of its level copied back |
| Run closes (`post_forecast`) | `output/forecast_report.html` copied to `output/<cycle>/<pass>/report_<couple>.html` |
| Pause (button, month change, test exit) | working files copied into the pass folders |
| Resume | working files replaced by the pass's copy, then its open run's kept uploads |
| Complete (`cycle_closed`) | working files copied into the pass folders |
| Abandon | `input/<cycle>/<pass>/` deleted; `output/<cycle>/<pass>/` emptied except the reports; working files emptied if the pass was active |

## 5. Migration

`_migrate_files` runs once per store (`PRAGMA user_version` 0 → 1): `uploads/<cycle>/<pass>/` (production) and
`uploads/dry_run/<cycle>/<pass>/` (test) move to the pass folders. Without an active pass, the working files are copied
into the last paused pass. Any other paused pass with an open run, or one whose files another run emptied since, gets
its run reset (`reset`, cause `pass_folders`): its fetches are redone on resume. The emptied `uploads/` folders stay.

## 6. Starting a pass at once (`POST /pipeline/passes`)

Seen by the owner on 2026-10-27: with the pass started only at the first launch, Start with "New pass" opened the
Dashboard on the month's **last pass**, the one just paused (`progress()` shows the active pass, else the month's
last one): it looked as if the paused pass came back. Decision: "New pass" + Start creates the pass at once.

- `POST /pipeline/passes?confirm=` → 201 `{id, cycle, state, started_at, started_by}`. Same rules as a launch that
  starts a pass: 409 `confirmation_required` after a complete or paused pass (impact `complete_pass` / `paused_pass`),
  refused while a job runs or a pass is active.
- It does what the first launch did: folders, uploads carried from the previous pass (F7), and the imports carried
  with the current parameters (`current_import_params()`, the same as an import launch).
- etlui Home: Start = `setCycle(month)` if it changed, then `startPass()`; the confirmation (`ImpactDialog`) is shown
  on Home, and its Confirm goes to the forecast page.

## 7. Not verified

- Migration on the real `logs/etlhub.db` and the test blob in Redis: not run.
- etlui against a real etlhub (the specs mock the API).
- R forecast outputs that are folders (copied with `copytree`, not seen in practice).
- The migration's copy of the working files into the last paused pass has no test.

Checks: `tests/infrastructure/test_checkpoint_store.py`
(`test_starting_a_pass_creates_it_at_once_with_its_folders_and_carried_items`, `test_a_new_pass_after_a_pause_needs_confirm_takes_its_uploads_and_abandon_keeps_only_reports`,
`test_two_months_in_turn_one_active_pass_at_a_time`, migration test), `tests/api/test_pipeline_router.py`
(`test_a_new_pass_starts_at_once_and_after_a_pause_with_confirm`); etlui `HomeView.spec.ts`.
