# Foreign keys in etlhub.db

Status: implemented 2026-11-18 (schema version 2).

## Problem

No table declared a `FOREIGN KEY`: every link was a plain column kept consistent by `CheckpointStore` alone. A future
bug or a hand edit could leave rows pointing to a pass that does not exist, and nothing would say so.

## Decision

- `pass_id REFERENCES passes(id)` on the 4 tables that carry it: `checkpoints`, `forecast_runs` (mandatory, part of
  their primary key), `pipeline_events`, `availability_checks` (nullable: NULL stays allowed).
- `PRAGMA foreign_keys = ON` on every store transaction (`_file_transaction`, `_memory_transaction`). SQLite leaves
  foreign keys off by default, per connection, and ignores the pragma inside a transaction: it is set before `BEGIN`.
- Migration 2 rebuilds the 4 tables (SQLite has no `ALTER TABLE ADD CONSTRAINT`): rename, create from `_SCHEMA`,
  copy, drop. `migrate()` keeps foreign keys off during the rebuild, then runs `PRAGMA foreign_key_check`: a row whose
  pass does not exist fails the migration and the db stays at version 1. `forecast_runs.external_data` (dbs from
  before 2026-10-12, unused) is not carried over. Event ids are kept, so the journal order is unchanged.
- Default actions (`NO ACTION`): no code deletes a pass, so no `ON DELETE CASCADE`.

## Links that stay without a foreign key

| Column | Why not |
|---|---|
| `pipeline_events.request_id` → `request_log` | the event is written during the request, the `request_log` row only after it (`api/middleware.py`); in test mode the events live in the Redis blob, `request_log` in the file; the 30-day purge deletes requests that test-mode events refer to |
| `cycle` (4 tables) | a month, not a row: there is no cycles table |
| `job_id` (3 tables) | jobs live in Redis (`JobStore`) |

## Rollback

`python -m etlhub.migrate` writes `logs/etlhub.db.v1-<time>.bak` (and `logs/test_mode.db.v1-<time>.bak` for the
test-mode db) before migrating. To go back: check out a commit at schema version 1 and restore them, API and workers
stopped (`db-migrations.md`, Procedure).

## ORM: not adopted

Checked on 2026-11-18 against `checkpoint_store.py` (about 1,230 lines, about 80 SQL calls, 8 tables, 68 tests).
Kept on `sqlite3` because:

- the store relies on SQLite itself: the in-memory db serialized into Redis (`serialize`/`deserialize`) for test mode,
  `BEGIN IMMEDIATE` as the pipeline lock, partial unique indexes, `PRAGMA user_version`, `VACUUM INTO`, `json_extract`.
  An ORM would not abstract these; they would stay raw SQL inside it;
- migrations move files (migration 1) and run on two dbs, one of them a Redis blob: Alembic would need custom wiring
  for both, and on SQLite it rebuilds tables the same way migration 2 does;
- rewriting the store is a large change in the module the whole pipeline depends on, for 8 small tables, and adds a
  dependency (none is installed today).

Revisit if: the store moves to PostgreSQL or another server db, another service writes these tables, or the schema
grows well past its current size.
