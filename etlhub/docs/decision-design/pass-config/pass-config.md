# Configuration fixed by a pass

Status: implemented 2026-11-20. Schema version 3: run `python -m etlhub.migrate` by hand (API and workers stopped) before starting this code. Until then the API refuses to start (`SchemaVersionError`).

> **Changed on 2026-11-23: DRYRUN = TEST MODE** (owner's rule). The DRYRUN rows below are superseded: a pass no longer
> chooses its DRYRUN. Test mode ⇒ every job is a dry run, production ⇒ every job writes to DHIS2. Home has no Dry run
> switch, `POST /pipeline/passes` and the launches take no `dry_run` (one sent is ignored), `.env`'s `DRYRUN` is the
> CLI's only. The `dry_run` column is still written (the mode's, journaled with `pass_started`) but never read: a pass
> started before, even in test mode with `dry_run = 0`, follows the mode (`CheckpointStore._passes`, `_check_config`).
> The other fixed values (GEE variables, PARENT_OU, LOG_LEVEL, DHIS2 URL) are unchanged.

> **Changed on 2026-11-24: the GEE variables are chosen in Import GEE**, no longer fixed when the pass starts
> ([../gee-import/gee-import.md](../gee-import/gee-import.md)). The GEE row below is superseded: Home has no checkboxes;
> each `POST /import_gee` may send `gee_variables`, written on the pass once the launch is accepted. PARENT_OU, LOG_LEVEL
> and the DHIS2 URL stay fixed as below.

## Decision

A pass fixes its whole configuration when it starts, and nothing changes it afterwards: not Admin Config, not `.env`, not another login, not the calendar.

| Fixed | Where it comes from when the pass starts | Column of `passes` |
|---|---|---|
| GEE variables | Home's checkboxes, over `pridec_gee.AVAILABLE_VARIABLES` (body `gee_variables`; absent: all; empty or unknown: 400) | `gee_variables` (comma-separated, in `pridec_gee`'s order; NULL: all) |
| DRYRUN | Home's Dry run switch (body `dry_run`; absent: true in test mode, else `DRYRUN` of `.env`) | `dry_run` |
| PARENT_OU, LOG_LEVEL | the editable config (Redis) at that moment | `parent_ou`, `log_level` |
| DHIS2 URL | the credential of the last login | `dhis_url` |
| Cycle | the target month (already the case) | `cycle` |

- `POST /pipeline/passes` fixes it (Home, "New pass"). A launch that starts a pass (no pass active) fixes the values of that moment, with every GEE variable and the launch's DRYRUN.
- Journaled with `pass_started` (its `detail`), returned with the pass everywhere (`GET /pipeline/checkpoints` `pass`, `GET /pipeline/cycles`).
- **Launches follow it** (`CheckpointStore._check_config`): a launch asking another `dry_run`, or from a session on another DHIS2 URL, is refused (409), nothing written. `update_key` in a dry-run pass is refused: only a pass started without dry run can update the key.
- **Jobs read their own pass's**: `CeleryTaskLauncher.launch` hands `pass_config` to the Celery task, `_run_task` puts it in `core/job_context.job_pass_config`, and `script_config._get` returns it for `GEE_VARIABLES`, `PARENT_OU`, `LOG_LEVEL` (`PASS_KEYS`). Outside a Celery job (the inline `post_forecast` / `update_key`, the import parameters, the availability check) it reads the active pass (`CheckpointStore.pass_config()`). `_dhis2_credential` refuses a credential whose URL is not the job's pass's (someone logged in elsewhere since the launch). The forecast's env file gets the pass's `PARENT_OU` and `LOG_LEVEL`.
- **No more automatic pause at a month change.** A pass stays active on its month until the user pauses, abandons or completes it. A new month's pass starts once the active one is paused or abandoned.
- `GEE_VARIABLES` left `config_store.EDITABLE_KEYS`: `GET /api/config` returns the variables of `pridec_gee`, read only; `PUT /api/config` no longer takes them. Admin Config edits PARENT_OU and LOG_LEVEL for the **next** passes.
- The import parameters (journaled with each launch, compared for carry-over and for reusing availability checks) follow the pass's GEE variables and PARENT_OU: a new pass with other values does not carry over an earlier import.

## Passes from before 2026-11-20

Migration 3 adds the columns as NULL: such a pass fixes nothing and behaves as before (Redis / `.env` values, the launch's DRYRUN or the default, no DHIS2 check), except the month change, which no longer pauses it.

## etlui

- Home: GEE checkboxes (all checked by default, Start disabled when none) and the Dry run switch for a new pass; a paused pass shows the values it started with, read only.
- Dashboard: DRYRUN shown read only (the pass's); "Import GEE: …" under the Data Import cards. A launch no longer sends `dry_run`.
- Admin Config: the GEE variables of `pridec_gee`, read only.

## Not changed

- The CLI (`etl/`) still reads everything, `GEE_VARIABLES` included, from its environment.
- `OU_LEVEL` and `DISEASE_CODE` come from each forecast run, as before.
- `.github/workflows/e2e-playwright.yml` still writes `GEE_VARIABLES` into `.env`: etlhub ignores it; the e2e scenario starts its pass with every variable unless it unchecks some on Home.
