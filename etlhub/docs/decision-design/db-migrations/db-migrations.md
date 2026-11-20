# Database migrations, by hand

Status: implemented 2026-11-04.

## Problem

Migrations of `logs/etlhub.db` and of the test-mode db (Redis `pipeline:dry_run:db`) ran by themselves, inside every
`CheckpointStore` transaction. A `git pull` or a branch checkout changed the data the first time the API or a worker
touched it, with no backup and no trace. Going back to an older commit then left that older code on a schema it did
not know (e.g. `checkpoints.pass_id` instead of `cycle`, files moved out of `uploads/`).

## Decision

- The schema has a number: `PRAGMA user_version`, `SCHEMA_VERSION = len(CheckpointStore.MIGRATIONS)`.
  `MIGRATIONS[i]` takes a db from version `i` to `i + 1`. Version 1 = passes (2026-10-22) + pass folders (2026-10-27).
- Migrations run **by hand only**: `python -m etlhub.migrate` (from anywhere; it moves to the repo root).
  It copies each db next to `etlhub.db` first (`etlhub.db.v<old>-<time>.bak`, `test_mode.db.v<old>-<time>.bak`),
  then applies every pending migration in one transaction.
  `--check` lists what is pending and exits 1 if anything is.
- Nothing else migrates. A new db is created at `SCHEMA_VERSION`. Any other db must be at `SCHEMA_VERSION`:
  - behind → the API refuses to start (`main.py` lifespan), and every pipeline read or write raises
    `SchemaVersionError` (so a worker job fails with the same message);
  - ahead (a newer etlhub migrated it) → refused too, by `migrate` as well: check out a newer version or restore
    the backup.

## Procedure

Update (git pull, checkout of a newer commit):

1. Stop the API and the workers.
2. `python -m etlhub.migrate --check`
3. If something is pending: copy `input/`, `output/` and `uploads/` if the migration moves files (migration 1 does),
   then `python -m etlhub.migrate`.
4. Start the API and the workers.

Going back to an older commit: there are no down-migrations. Restore the backup taken before the migration:

```bash
cp logs/etlhub.db.v1-<time>.bak logs/etlhub.db   # also delete logs/etlhub.db-wal and -shm, API stopped
base64 -w0 logs/test_mode.db.v1-<time>.bak | redis-cli -x SET pipeline:dry_run:db
```

Commits made before 2026-11-04 do not have the version check: they still migrate on their own and do not refuse a
newer db.

## Rule for every change to the tables

A change to `_SCHEMA` (table, column, index) ships in the same commit with:

1. a new function at the end of `CheckpointStore.MIGRATIONS` (never edit a released one: some db already ran it);
2. its test: a db built at the previous version, `migrate()`, then the behaviour on the migrated data;
3. a line in this file's history.

`CREATE TABLE IF NOT EXISTS` in `_SCHEMA` only serves new dbs: an existing db gets a new table through its migration.

## Limits

- ponytail: the backup holds the dbs, not the files a migration moves (`input/`, `output/`, `uploads/`); copy them by
  hand first. Add them to the backup if a future migration moves files again.
- The workers check the version at their first pipeline transaction, not at start.
- `request_log` (same file, `RequestTracker`) is outside this versioning: its table is created if missing.
- CI: the unit tests build their dbs in `tmp_path`, so they always start at `SCHEMA_VERSION`; the migration tests
  (`tests/infrastructure/test_checkpoint_store.py`, "schema migrations") are what checks the migrations there.

## History

| Version | Date | Change |
|---|---|---|
| 1 | 2026-10-22, 2026-10-27 | month-keyed store → passes; `uploads/` → pass folders (numbered on 2026-11-04) |
| 2 | 2026-11-18 | `FOREIGN KEY pass_id → passes(id)` on `checkpoints`, `forecast_runs`, `pipeline_events`, `availability_checks` (tables rebuilt; `forecast_runs.external_data` dropped); `PRAGMA foreign_keys = ON` in the store's transactions. See `../foreign-keys/foreign-keys.md` |
| 3 | 2026-11-20 | `passes` gets the configuration a pass fixes when it starts: `gee_variables`, `parent_ou`, `log_level`, `dry_run`, `dhis_url` (nullable, `ALTER TABLE ADD COLUMN`; existing passes keep NULL). Moves no file. See `../pass-config/pass-config.md` |
