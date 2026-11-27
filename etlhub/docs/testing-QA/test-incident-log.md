# etlhub — Test incident log

Incidents met while testing the pipeline by hand. One entry per incident, newest first: what was seen, what the state was, the cause, the fix. Bugs that stay open go to [`known-issues.md`](../known-issues.md).

## 2026-10-14 — "Alert thresholds (CSB only)" cannot run: CSB runs blocked before approval

**Status: worked around, to implement later. Ignore for now.**

**Seen.** In the CSB/Malaria run, launching "Alert thresholds (CSB only)" (`CSB/Malaria:calc_orgunit_alerts`) answered `501 {"message": "calc_orgunit_alerts is not implemented: no script exists for it yet"}`. "Your approval" (`approve`) needs it in success (`run_items` in `domain/pipeline.py`), so no CSB run, and therefore no cycle, could get past it.

**Cause.** `POST /calc_orgunit_alerts` is a stub (`api/routers/etl/analytics_router.py`): no script exists for it yet. The target is `pridec etl calc_orgUnit_alerts` (`.claude/skills/etlhub/references/reference.md`).

**Workaround (temporary).** A "Skip" button replaces "Launch" on that item:
- etlhub: `POST /pipeline/runs/current/skip_alerts` → `CheckpointStore.skip_alerts()` marks the open CSB run's `calc_orgunit_alerts` as success without running anything. It goes through the same checks as a launch: no job running, a run is open, the run is a CSB run, and `forecast` is in success.
- etlui: `skipAlerts()` in `services/pipeline.ts` and `usePipeline.ts`. In the run's Steps dialog, the `LevelColumn.vue` button reads "Skip", and `launchItem` in `Dashboard.vue` routes it to `skipAlerts`.
- A skipped item looks like a normal success (`job_id` empty). **CSB org unit alerts are not computed.**

**To do later.** Implement the `calc_orgunit_alerts` script and its launch route. Then remove the workaround: `skip_alerts` (store, `PipelineGate`, route, endpoint-table row), `skipAlerts` (etlui service, composable, `Dashboard.vue`, the `'Skip'` label in `LevelColumn.vue`), and the skip part of `test_a_csb_run_needs_calc_orgunit_alerts_before_approval` together with `test_skip_alerts_is_refused_outside_a_csb_run`. `skip_alerts()` in `checkpoint_store.py`, `LevelColumn.vue` and `Dashboard.vue` carry a `ponytail:` comment (`/ponytail-debt` lists them).

## 2026-10-14 — "Data check" disabled in the CSB/Malaria run

**Seen.** In the Dashboard, the run Health Centres (CSB/Malaria) showed the item "Data check" (`CSB/Malaria:validate_inputs`) disabled.

**State (read-only, no API call).**
- `DRYRUN=true` in Redis (`app:config:dynamic`), so the active checkpoints were the test-mode db (Redis key `pipeline:dry_run:db`), not `logs/etlhub.db`.
- Cycle `202504`. ADJ/Malaria and COM/Malaria closed, CSB/Malaria open, no job lock.
- Prerequisites of `CSB/Malaria:validate_inputs` (`domain/pipeline.py`, `run_items`):

| Prerequisite | Status |
|---|---|
| `config/Malaria` | success |
| `external_data/csb` | **pending** |
| `CSB/Malaria:fetch_disease` | success |
| `CSB/Malaria:fetch_climate` | success |
| `CSB/Malaria:fetch_geojson` | success |

`blocking_reason()` returned `CSB/Malaria:validate_inputs needs forecast/external_data/csb in success first`, so `launchable` was `false` and the UI disabled the button. This was rule R2: an item starts only when its prerequisites are in success.

**Cause.** `external_data.csv` is one item per org unit level (`LEVEL` in `domain/pipeline.py`). ADJ and COM are level `fkt` and share `external_data/fkt`. CSB is level `csb` and needs its own `external_data/csb`, which had never been uploaded in this cycle. The earlier ADJ/COM runs had uploaded only the `fkt` file.

**Fix.** Upload `external_data.csv` for the CSB level in the CSB/Malaria run. "Data check" then became launchable. No code change.

**Note.** In production mode, `logs/etlhub.db` (cycle `202610`) would have blocked earlier, on step `data_import`, because `approve_imports` was still `pending`.
