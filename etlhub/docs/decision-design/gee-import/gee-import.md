# GEE variables chosen in Import GEE, one import state per variable

Status: implemented on 2026-11-24 (owner's request and choices G1–G4 of the same day). No schema change: the pass's
`gee_variables` column (pass-config.md, migration 3) is reused. Not run against GEE or a DHIS2: tested with
`pridec_gee` and DHIS2 replaced.

## Decision

| # | Decision | Before |
|---|---|---|
| 1 | The GEE variables are chosen in etlui's Import GEE dialog (the Import GEE card of Data Import opens it), at each launch | Home's checkboxes, fixed when the pass started |
| 2 | `POST /import_gee` takes an optional body `{gee_variables: [...]}` (empty or unknown: 400). Once the gate accepts the launch, the choice is written on the active pass (`passes.gee_variables`), in the same transaction (a 409 changes nothing); a launch that starts a pass gives it to the new pass. Without a body: the pass's choice (NULL: all) | no body |
| 3 | Each chosen variable has its own import state (G1): one GEE fetch of every chosen variable, then one post per variable of its values only | one fetch, one post of everything |
| 4 | A failed post does not stop the others (G2); the job ends in error when one failed | n/a |
| 5 | A new pass has every variable checked (G3: `gee_variables` NULL), then the dialog shows the pass's last choice | Home: all checked |
| 6 | Relaunching after a success keeps the 409 confirmation (G4); etlui resends the same choice with `confirm=true` | same |
| 7 | `POST /pipeline/passes` still accepts `gee_variables` (API compatibility); etlui sends none | Home sent them |

## Why one fetch, then one post per variable

`pridec_gee.fetch_climate_gee` computes a source's variables together (ERA5, Sentinel-2) and returns all of them even
when one is asked. Fetching per variable would multiply the GEE computation; posting the whole frame (the old
`etl/scripts/import_gee.py`, `import_pridec_climate`) also posted variables nobody checked. The job
(`application/use_cases/gee_import.py`) fetches once, then posts, per chosen variable, the rows whose `dataElement`
is that variable: an unchecked variable is never posted. A failed fetch fails every chosen variable.

## States

Kept in Redis through the `FetchedImports` port (key `pivot_fetched:<mode>:<pass>:import_gee`, the Pivot fetches' store),
per pass and mode, replaced whole by the next import: `{variable, status: running | imported | empty | failed, at,
dry_run, error, rows}`. `GET /pipeline/imports/gee` lists every variable of `pridec_gee` with `chosen` (the pass shown's
choice) and `state` (null: never imported in the pass; else the stored item, `variable` included). etlui reads it when
the dialog opens, then at each new pipeline state while the dialog is open (`usePipeline` reads one every 3 s while a
job runs, and after each action).

## Not changed

- `etl/scripts/import_gee.py` (the CLI's) and `pridec_gee`. The job copies the script's GEE setup (key file, rice
  fields, `calc_date_range(3)`, fokontany level 6); a change to one must be made to the other (`ponytail:` note).
- The carry-over of imports (cycle-passes.md § 11) and the availability check compare the launch's parameters, which
  now carry the dialog's choice (`current_import_params(gee_variables=...)`).
- `pass_config()` still hands the pass's configuration to the job: the job reads the choice through `get_gee_variables()`.

## Not verified

- A real run (GEE, DHIS2): never launched without the owner's approval.
- The extra cost of N posts instead of one (each is a `dataValueSets` request with `CREATE_AND_UPDATE`).
- Whether DHIS2 accepts each variable's payload exactly as it accepted the combined one (same rows, split by `dataElement`).
