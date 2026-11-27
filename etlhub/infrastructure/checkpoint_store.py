import base64
import json
import logging
import shutil
import sqlite3
import uuid
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, closing, contextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir
from etlhub.core.request_context import request_context
from etlhub.domain import pipeline
from etlhub.domain.exceptions import ConfirmationRequiredError, ETLException, PipelineBlockedError
from etlhub.domain.pipeline import (
    COUPLES, DISEASES, IMPORT_TASKS, LEVEL, accessible_steps, blocking_reason, config_item, dependents,
    external_data_item, impact, progress, require_confirmation, require_input_confirmation, resolve_slot,
    run_context, run_items, status,
)
from etlhub.infrastructure.config_store import ConfigStore
from etlhub.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

# Same db as request_log, but no retention: a cycle must stay readable.
# A pass is one run of a cycle (month): its checkpoints, forecast runs and journal events carry its id
# (etlhub/docs/decision-design/cycle-passes/cycle-passes.md).
_PASSES = """CREATE TABLE IF NOT EXISTS passes (
    id         TEXT PRIMARY KEY,
    cycle      TEXT NOT NULL,
    state      TEXT NOT NULL,  -- active | paused | complete | abandoned
    started_at TEXT NOT NULL,
    started_by TEXT,
    -- Its configuration, fixed when it started (pass-config.md); all NULL for a pass from before 2026-11-20.
    gee_variables TEXT,  -- chosen on Home, comma-separated; NULL: every variable of pridec_gee
    parent_ou     TEXT,
    log_level     TEXT,
    dry_run       INTEGER,
    dhis_url      TEXT,
    pivot_url     TEXT   -- since 2026-11-27 (migration 4); NULL: the editable config's (Redis), as before
)"""
_SCHEMA = _PASSES + """;
CREATE UNIQUE INDEX IF NOT EXISTS one_active_pass ON passes(state) WHERE state = 'active';
CREATE TABLE IF NOT EXISTS checkpoints (
    pass_id    TEXT NOT NULL REFERENCES passes(id),
    step       TEXT NOT NULL,
    item       TEXT NOT NULL,
    job_id     TEXT,
    status     TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (pass_id, step, item)
);
CREATE INDEX IF NOT EXISTS ix_checkpoints_job_id ON checkpoints(job_id);
CREATE TABLE IF NOT EXISTS pipeline_lock (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    job_id      TEXT NOT NULL,
    task        TEXT NOT NULL,
    acquired_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS forecast_runs (
    pass_id       TEXT NOT NULL REFERENCES passes(id),
    couple        TEXT NOT NULL,
    state         TEXT NOT NULL,
    disease_code  TEXT NOT NULL,
    ou_level      TEXT NOT NULL,
    alert_name    TEXT,
    opened_at     TEXT NOT NULL,
    closed_at     TEXT,
    PRIMARY KEY (pass_id, couple, opened_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_run_per_pass ON forecast_runs(pass_id) WHERE state = 'open';
CREATE TABLE IF NOT EXISTS pipeline_cycle (  -- the target month of launches; no row = the calendar month
    id    INTEGER PRIMARY KEY CHECK (id = 1),
    cycle TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pipeline_events (  -- the journal: appended in the transaction of each change, never updated
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle      TEXT NOT NULL,
    at         TEXT NOT NULL,
    step       TEXT,
    item       TEXT,
    event      TEXT NOT NULL,
    job_id     TEXT,
    actor      TEXT,
    request_id TEXT,
    detail     TEXT,
    pass_id    TEXT REFERENCES passes(id)  -- NULL: a mode_changed with no active pass
);
CREATE INDEX IF NOT EXISTS ix_pipeline_events_pass ON pipeline_events(pass_id, id);
CREATE INDEX IF NOT EXISTS ix_pipeline_events_job_id ON pipeline_events(job_id);
CREATE TABLE IF NOT EXISTS availability_checks (  -- sections of GET /import_availability, shared by the cycle's users
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle          TEXT NOT NULL,
    pass_id        TEXT REFERENCES passes(id),  -- NULL: checked before the month's first launch
    task           TEXT NOT NULL,
    params         TEXT NOT NULL,  -- JSON of what the section checked: dhis_url, task, elements, periods, org_units
    checked_at     TEXT NOT NULL,  -- when the check started, local time like pipeline_events.at
    checked_by     TEXT,
    section        TEXT NOT NULL,  -- JSON section of the report
    last_analytics TEXT
);
CREATE INDEX IF NOT EXISTS ix_availability_checks ON availability_checks(cycle, task, checked_at);
"""
# Databases created before 2026-10-12 also have an external_data column (DEFAULT 'none'): unused, inserts skip it.
_RUN_COLUMNS = ("pass_id", "couple", "state", "disease_code", "ou_level", "alert_name", "opened_at")
_EVENT_COLUMNS = ("cycle", "pass_id", "at", "step", "item", "event", "job_id", "actor", "request_id", "detail")
# The configuration of a pass, fixed when it starts: what its jobs read (script_config._get), never Redis or .env.
PASS_CONFIG = ("gee_variables", "parent_ou", "log_level", "dry_run", "dhis_url", "pivot_url")
_PASS_COLUMNS = ("id", "cycle", "state", "started_at", "started_by", *PASS_CONFIG)
_AVAILABILITY_DAYS = 30  # a stored check older than this is checked again (decision 2026-10-26)
# Pass folders (etlhub/docs/decision-design/pass-folders/pass-folders.md): input/<cycle>/<pass>/ and output/<cycle>/<pass>/.
# They keep the uploads (item -> file name) and the reports of closed runs for good, and a copy of the working files
# (the rest of input/ and output/) while the pass is not active.
_KEPT_INPUTS = {**{f"config/{d}": f"config_{d}.json" for d in DISEASES},
                **{f"external_data/{lv}": f"external_data_{lv}.csv" for lv in sorted(set(LEVEL.values()))}}
_KEPT = set(_KEPT_INPUTS.values()) | {f"report_{c.replace('/', '_')}.html" for c in COUPLES}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _now_us() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def _actor(actor: str | None = None) -> str | None:
    """Who acts: the given actor, else the logged-in user of the HTTP request, else the worker."""
    context = request_context.get()
    return actor or (context.get("actor") if context is not None else "worker")


class SchemaVersionError(RuntimeError):
    """A db (etlhub.db or the test blob) is not at SCHEMA_VERSION: python -m etlhub.migrate, by hand."""


def _schema_version(conn: sqlite3.Connection) -> int | None:
    """PRAGMA user_version, or None for a new db (no checkpoints table: request_log may be there already)."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'checkpoints'").fetchone():
        return None
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _schema_error(where: str, version: int) -> SchemaVersionError:
    if version > SCHEMA_VERSION:
        return SchemaVersionError(
            f"{where} is at schema version {version}, newer than this code ({SCHEMA_VERSION}): check out a newer "
            f"version, or restore the *.v{SCHEMA_VERSION}-*.bak backup that python -m etlhub.migrate left in logs/")
    return SchemaVersionError(
        f"{where} is at schema version {version}, this code needs {SCHEMA_VERSION}: stop the API and the workers, "
        "then run python -m etlhub.migrate (it backs the db up first)")


def _migrate_to_passes(conn: sqlite3.Connection, uploads: Path) -> None:
    """Part of migration 1: a store keyed by month to passes (2026-10-22). The journal of a month is cut after each
    cycle_closed; its checkpoints and kept files go to its last pass, each forecast run to the pass it was opened in.
    """
    if "cycle" not in {r[1] for r in conn.execute("PRAGMA table_info(checkpoints)")}:
        return  # new or already migrated
    conn.execute("ALTER TABLE checkpoints RENAME COLUMN cycle TO pass_id")
    conn.execute("ALTER TABLE forecast_runs RENAME COLUMN cycle TO pass_id")
    conn.execute("DROP INDEX IF EXISTS one_open_run")
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'pipeline_events'").fetchone():
        conn.execute("ALTER TABLE pipeline_events ADD COLUMN pass_id TEXT")
        conn.execute("DROP INDEX IF EXISTS ix_pipeline_events_cycle")
    conn.execute(_PASSES)  # not executescript: it would commit the caller's transaction
    target = CheckpointStore._target(conn)
    months = {m for (m,) in conn.execute("SELECT pass_id FROM checkpoints UNION SELECT pass_id FROM forecast_runs"
                                         " UNION SELECT cycle FROM pipeline_events")}
    for month in sorted(months):
        passes, closed = [], True
        for event_id, event, actor, at in conn.execute(
                "SELECT id, event, actor, at FROM pipeline_events WHERE cycle = ? ORDER BY id", (month,)).fetchall():
            if closed and event not in ("mode_changed", "cycle_chosen"):  # those never start a pass
                passes.append({"id": uuid.uuid4().hex[:8], "started_at": at, "started_by": actor, "events": []})
                closed = False
            if passes:
                passes[-1]["events"].append(event_id)
            closed = closed or event == "cycle_closed"
        rows = CheckpointStore._rows(conn, month)
        if rows and not passes:  # a cycle from before the journal
            first = min(r["updated_at"] for r in rows.values())
            passes.append({"id": uuid.uuid4().hex[:8], "started_at": first, "started_by": None, "events": []})
            closed = False
        for i, p in enumerate(passes):
            done = i < len(passes) - 1 or closed or (rows and progress(rows)["current_step"] is None)
            state = "complete" if done else "active" if month == target else "paused"
            conn.execute("INSERT INTO passes (id, cycle, state, started_at, started_by) VALUES (?, ?, ?, ?, ?)",
                         (p["id"], month, state, p["started_at"], p["started_by"]))
            conn.executemany("UPDATE pipeline_events SET pass_id = ? WHERE id = ?", [(p["id"], e) for e in p["events"]])
        for i, p in reversed(list(enumerate(passes))):  # each run to the last pass started before it opened
            conn.execute("UPDATE forecast_runs SET pass_id = ? WHERE pass_id = ? AND opened_at >= ?",
                         (p["id"], month, p["started_at"] if i else ""))
        if passes:
            conn.execute("UPDATE checkpoints SET pass_id = ? WHERE pass_id = ?", (passes[-1]["id"], month))
            kept = [f for f in (uploads / month).glob("*") if f.is_file()]
            for f in kept:
                (uploads / month / passes[-1]["id"]).mkdir(parents=True, exist_ok=True)
                f.rename(uploads / month / passes[-1]["id"] / f.name)


def _is_cycle(name: str) -> bool:
    """input/<cycle>/ and output/<cycle>/ hold the pass folders; everything else there is working files."""
    return len(name) == 6 and name.isdigit()


def _is_kept(name: str) -> bool:
    return name in _KEPT


def _clear(directory: Path, skip: Callable[[str], bool]) -> None:
    """Deletes what directory holds, except the names skip keeps."""
    for path in directory.iterdir() if directory.is_dir() else ():
        if skip(path.name):
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


def _copy_work(src: Path, dst: Path, skip_src: Callable[[str], bool], skip_dst: Callable[[str], bool]) -> None:
    """Replaces the working files of dst by those of src (skipped names are left as they are on both sides)."""
    _clear(dst, skip_dst)
    dst.mkdir(parents=True, exist_ok=True)
    for path in src.iterdir() if src.is_dir() else ():
        if skip_src(path.name):
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.copytree(path, dst / path.name, symlinks=True)
        else:
            shutil.copy2(path, dst / path.name, follow_symlinks=False)


def apply_to_config_store(context: dict[str, str | None]) -> None:
    """Writes the run context where the ETL scripts read it (etl/scripts/config.py reads Redis first)."""
    store = ConfigStore()
    written = store.set_all({k: v for k, v in context.items() if v is not None})
    cleared = store.delete_keys([k for k, v in context.items() if v is None])
    if not (written and cleared):
        raise ETLException("Could not write the forecast run context (DISEASE_CODE, OU_LEVEL) to Redis")


def live_pass_config() -> dict:
    """What a new pass fixes besides its GEE variables and DRYRUN: PARENT_OU, LOG_LEVEL and PIVOT_URL of the editable
    config (Redis, never through script_config: it reads the active pass) and the DHIS2 URL of the last login."""
    from etlhub.infrastructure.auth_store import get_credential
    config = ConfigStore().get_all()
    return {"parent_ou": config.get("PARENT_OU"), "log_level": config.get("LOG_LEVEL"),
            "pivot_url": config.get("PIVOT_URL"), "dhis_url": (get_credential() or {}).get("url")}


class RedisBlob:
    """The test-mode checkpoint db: an in-memory SQLite, serialized into one Redis key.

    ponytail: the whole db is rewritten at each transaction; fine for a few hundred rows, a real Redis schema if it grows.
    """
    KEY = "pipeline:dry_run:db"

    def get(self) -> bytes | None:
        value = get_redis().get(self.KEY)
        return base64.b64decode(value) if value else None  # the shared client decodes strings: base64

    def set(self, data: bytes) -> None:
        get_redis().set(self.KEY, base64.b64encode(data).decode())

    def delete(self) -> None:
        get_redis().delete(self.KEY)

    def lock(self):
        # Serializes test-mode transactions across the API and the workers, like BEGIN IMMEDIATE does on the file.
        return get_redis().lock("pipeline:dry_run:lock", timeout=60, blocking_timeout=5)


class CheckpointStore:
    """Pipeline checkpoints (one fact per item and cycle), forecast runs and the single job lock, in SQLite."""

    def __init__(self, db_path: str | Path | None = None, data_dir: str | Path | None = None,
                 apply_context: Callable[[dict], None] = apply_to_config_store,
                 test_mode: Callable[[], bool] = current_test_mode,
                 blob: RedisBlob | None = None, live_config: Callable[[], dict] = live_pass_config):
        """In test mode everything is kept in Redis (`blob`) and test/input, test/output; never in the SQLite file,
        except the single job lock of both modes. test_mode: the mode of the request or job served (the user's).

        The Redis keys and the uploads folder keep their dry_run names: they hold the test state of before TEST_MODE.
        """
        settings = get_settings()
        self._test_mode = test_mode
        self._blob = blob or RedisBlob()
        self._db_path = Path(db_path or Path(settings.logs_dir) / "etlhub.db")
        self._data_dir = Path(data_dir or settings.data_dir)
        self._uploads_root = self._data_dir / "uploads"  # before the pass folders (2026-10-27): read by the migrations only
        self._apply_context = apply_context
        self._live_config = live_config

    @property
    def _input_dir(self) -> Path:
        """input/ of the mode served: ./input in production, test/input in test."""
        return work_dir(self._data_dir, "input", self._test_mode())

    @property
    def _output_dir(self) -> Path:
        return work_dir(self._data_dir, "output", self._test_mode())

    # --- helpers (inside a transaction) ---------------------------------------------------

    @contextmanager
    def _transaction(self, read: bool = False) -> Iterator[sqlite3.Connection]:
        """Same SQL in both modes: the SQLite file in production, an in-memory copy kept in Redis in test mode.
        read=True: the block writes nothing, so in production it takes no write lock (see _file_transaction)."""
        with self._mode_transaction(self._test_mode(), read) as conn:
            yield conn

    def _mode_transaction(self, test_mode: bool, read: bool = False) -> AbstractContextManager[sqlite3.Connection]:
        # ponytail: test mode ignores read (Redis lock, BEGIN IMMEDIATE on the attached file, blob saved back);
        # pass it to _memory_transaction if test-mode reads ever hold up production launches.
        return self._memory_transaction() if test_mode else self._file_transaction(read)

    @contextmanager
    def _memory_transaction(self) -> Iterator[sqlite3.Connection]:
        with self._blob.lock(), closing(sqlite3.connect(":memory:", isolation_level=None)) as conn:
            data = self._blob.get()
            if data:
                conn.deserialize(data)
            self._check_schema(conn, _BLOB)  # a failure saves nothing: the blob is set at the end
            conn.execute("PRAGMA foreign_keys = ON")  # off by default, per connection, ignored inside a transaction
            # The job lock of both modes is the file's: attached, and taken up front with it (IMMEDIATE covers every
            # attached db). Order Redis lock, then file; a production transaction never takes the Redis lock.
            # The file may exist without the schema: RequestTracker creates it with request_log alone at the first request.
            if not self._db_path.is_file() or not self._file_has_schema():
                with self._file_transaction():  # creates the file and its schema
                    pass
            conn.execute("ATTACH DATABASE ? AS shared", (str(self._db_path),))
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            self._blob.set(conn.serialize())

    def _file_has_schema(self) -> bool:
        with closing(sqlite3.connect(self._db_path, timeout=5)) as conn:
            return _schema_version(conn) is not None

    @contextmanager
    def _file_transaction(self, read: bool = False) -> Iterator[sqlite3.Connection]:
        # BEGIN IMMEDIATE takes the write lock up front: two launches cannot both see the lock free.
        # A read (read=True: the block must write nothing) takes a deferred BEGIN: under WAL a reader does not wait for a writer.
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._db_path, timeout=5, isolation_level=None)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            self._check_schema(conn, str(self._db_path))
            conn.execute("PRAGMA foreign_keys = ON")  # off by default, per connection, ignored inside a transaction
            conn.execute("BEGIN" if read else "BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    @staticmethod
    def _rows(conn: sqlite3.Connection, pass_id: str) -> pipeline.Rows:
        rows = conn.execute(
            "SELECT step, item, status, job_id, updated_at FROM checkpoints WHERE pass_id = ?", (pass_id,)
        ).fetchall()
        return {(s, i): {"status": st, "job_id": j, "updated_at": u} for s, i, st, j, u in rows}

    @staticmethod
    def _target(conn: sqlite3.Connection) -> str:
        """The month launches go to: the one chosen with set_cycle (or resumed), else the calendar month."""
        row = conn.execute("SELECT cycle FROM pipeline_cycle").fetchone()
        return row[0] if row else pipeline.this_month()

    @staticmethod
    def _set_target(conn: sqlite3.Connection, cycle: str) -> None:
        conn.execute("DELETE FROM pipeline_cycle")
        if cycle != pipeline.this_month():  # the calendar month: follow the calendar
            conn.execute("INSERT INTO pipeline_cycle (id, cycle) VALUES (1, ?)", (cycle,))

    def _passes(self, conn: sqlite3.Connection, where: str = "1", params: tuple = ()) -> list[dict]:
        """Passes, oldest first. SELECT *: migration 1 reads passes from before PASS_CONFIG (migration 3).
        dry_run is the mode's (DRYRUN = TEST MODE, since 2026-11-23): the value a pass stored when it started is not used."""
        cursor = conn.execute(f"SELECT * FROM passes WHERE {where} ORDER BY started_at", params)
        passes = [dict(zip([c[0] for c in cursor.description], r)) for r in cursor]
        for p in passes:
            p["dry_run"] = self.default_dry_run()  # a store's db holds the passes of one mode, the one served
        return passes

    def _get_pass(self, conn: sqlite3.Connection, pass_id: str | None) -> dict | None:
        return next(iter(self._passes(conn, "id = ?", (pass_id,))), None)

    def _active(self, conn: sqlite3.Connection) -> dict | None:
        return next(iter(self._passes(conn, "state = 'active'")), None)

    def _pass_of(self, conn: sqlite3.Connection, pass_id: str | None) -> dict:
        """The pass of a job (its launched event), else the active one, else the target month without a pass."""
        return self._get_pass(conn, pass_id) or self._active(conn) or {"id": None, "cycle": self._target(conn)}

    def _set_state(self, conn: sqlite3.Connection, p: dict, state: str, cause: str, actor: str | None = None,
                   reason: str | None = None) -> None:
        conn.execute("UPDATE passes SET state = ? WHERE id = ?", (state, p["id"]))
        p["state"] = state
        if state == "paused":  # the working files go with the pass, to come back on resume
            self._save_work(p)
        detail = {"cause": cause, **({"reason": reason} if reason else {})}
        self._event(conn, p, "resumed" if state == "active" else state, detail=detail, actor=actor)

    def _current(self, conn: sqlite3.Connection, confirm: bool | None = None, config: dict | None = None) -> dict:
        """The active pass, which every write goes to. Raises PipelineBlockedError without one.

        A launch (confirm not None) starts a pass on the target month; after a complete or paused pass, only with
        confirm=true (ConfirmationRequiredError otherwise). A paused pass stays paused, to resume from the Journal.
        config: the configuration of a new pass (_config), fixed for it and journaled with pass_started.
        A pass stays active until the user pauses, abandons or completes it, the month changing or not (2026-11-20).
        """
        active = self._active(conn)
        if active:
            return active
        cycle = self._target(conn)
        last = next(reversed(self._passes(conn, "cycle = ?", (cycle,))), None)
        paused = last is not None and last["state"] == "paused"
        if confirm is None:
            raise PipelineBlockedError(
                f"Pass {last['id']} of cycle {cycle} is paused: resume it from the Journal, or launch a job of step "
                "data_import to start a new pass" if paused else
                f"No active pass in cycle {cycle}: launch a job of step data_import to start one")
        redo = last is not None and last["state"] in ("complete", "paused")
        if redo and not confirm:
            raise ConfirmationRequiredError(
                f"Pass {last['id']} of cycle {cycle} is paused: resend with confirm=true to start a new pass "
                "(it stays paused, to resume from the Journal)" if paused else
                f"Cycle {cycle} is complete: resend with confirm=true to start a new pass (the complete one is kept)",
                {"cycle": cycle, "paused_pass" if paused else "complete_pass": last["id"]})
        config = {c: (config or {}).get(c) for c in PASS_CONFIG}
        p = {"id": uuid.uuid4().hex[:8], "cycle": cycle, "state": "active", "started_at": _now_us(),
             "started_by": _actor(), **config}
        conn.execute(f"INSERT INTO passes ({', '.join(_PASS_COLUMNS)}) VALUES ({', '.join('?' * len(_PASS_COLUMNS))})",
                     tuple(p[c] for c in _PASS_COLUMNS))
        detail = {**({"cause": "redo"} if redo else {}), **{k: v for k, v in config.items() if v is not None}}
        self._event(conn, p, "pass_started", detail=detail or None)
        return {**p, "new": True}  # start() carries the previous passes' imports over to it

    @staticmethod
    def _open_run(conn: sqlite3.Connection, pass_id: str | None) -> dict | None:
        row = conn.execute(f"SELECT {', '.join(_RUN_COLUMNS)} FROM forecast_runs WHERE state = 'open' AND pass_id = ?",
                           (pass_id,)).fetchone()
        return dict(zip(_RUN_COLUMNS, row)) if row else None

    @staticmethod
    def _lock_table(conn: sqlite3.Connection) -> str:
        """The single job lock of both modes: the SQLite file's table (attached as `shared` in test mode)."""
        attached = any(row[1] == "shared" for row in conn.execute("PRAGMA database_list"))
        return "shared.pipeline_lock" if attached else "pipeline_lock"

    @staticmethod
    def _owns(conn: sqlite3.Connection, job_id: str) -> bool:
        """Whether the job belongs to this connection's mode (its journal or checkpoints name it)."""
        return bool(conn.execute("SELECT 1 FROM pipeline_events WHERE job_id = ?"
                                 " UNION SELECT 1 FROM checkpoints WHERE job_id = ?", (job_id, job_id)).fetchone())

    def _lock(self, conn: sqlite3.Connection) -> dict | None:
        """The job holding the lock; one of the other mode only as such (no task, no id: never readable here)."""
        row = conn.execute(f"SELECT job_id, task, acquired_at FROM {self._lock_table(conn)}").fetchone()
        if not row:
            return None
        if not self._owns(conn, row[0]):
            row = (None, "a job of the other mode", row[2])
        return dict(zip(("job_id", "task", "acquired_at"), row))

    def _check_lock_free(self, conn: sqlite3.Connection) -> None:
        # The lock never expires: a killed worker keeps it until DELETE /pipeline/lock. One job at a time, both modes.
        if lock := self._lock(conn):
            job = f"{lock['task']} ({lock['job_id']})" if lock["job_id"] else "A job of the other mode"
            raise PipelineBlockedError(f"{job} is running since {lock['acquired_at']}: one job at a time")

    def _take_lock(self, conn: sqlite3.Connection, job_id: str, task: str) -> None:
        conn.execute(f"INSERT INTO {self._lock_table(conn)} (id, job_id, task, acquired_at) VALUES (1, ?, ?, ?)",
                     (job_id, task, _now()))

    def _free_lock(self, conn: sqlite3.Connection, job_id: str) -> None:
        conn.execute(f"DELETE FROM {self._lock_table(conn)} WHERE job_id = ?", (job_id,))

    @staticmethod
    def _upsert(conn: sqlite3.Connection, p: dict, step: str, item: str, job_id: str | None, state: str) -> None:
        conn.execute(
            "INSERT INTO checkpoints (pass_id, step, item, job_id, status, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (pass_id, step, item) DO UPDATE SET"
            " job_id = excluded.job_id, status = excluded.status, updated_at = excluded.updated_at",
            (p["id"], step, item, job_id, state, _now()),
        )

    @staticmethod
    def _delete(conn: sqlite3.Connection, p: dict, items: list[str]) -> list[str]:
        """Back to pending = no row (forecast step only). Returns the items that had a row."""
        return [i for i in items if conn.execute(
            "DELETE FROM checkpoints WHERE pass_id = ? AND step = 'forecast' AND item = ?", (p["id"], i)).rowcount]

    def _reset(self, conn: sqlite3.Connection, p: dict, items: list[str], cause: str,
               job_id: str | None = None) -> None:
        """_delete, journaled when it reset something."""
        if reset := self._delete(conn, p, items):
            self._event(conn, p, "reset", "forecast", job_id=job_id, detail={"items": reset, "cause": cause})

    @staticmethod
    def _event(conn: sqlite3.Connection, p: dict, event: str, step: str | None = None, item: str | None = None,
               job_id: str | None = None, detail: dict | None = None, actor: str | None = None) -> None:
        """Appends to the journal of pass p, in the caller's transaction: the event exists if and only if the change does.

        The actor and the request come from the HTTP request (core/request_context.py); without one, the worker acts.
        ponytail: the request flags are set before the commit, so a request refused later in the same transaction
        (rare: an automatic pause, then a 409) is kept out of the purge too; harmless.
        """
        context = request_context.get()
        conn.execute(f"INSERT INTO pipeline_events ({', '.join(_EVENT_COLUMNS)}) VALUES ({', '.join('?' * len(_EVENT_COLUMNS))})",
                     (p["cycle"], p["id"], _now_us(), step, item, event, job_id, _actor(actor),
                      context and context["request_id"], json.dumps(detail) if detail else None))
        if context is not None:
            context["pipeline"] = True
            if conn.execute("PRAGMA database_list").fetchone()[2]:  # a file: production (test mode is in memory)
                context["journal"] = True

    def _pass_dir(self, p: dict, root: Path | None = None) -> Path:
        """The pass folder: input/<cycle>/<pass>/ (uploads), or output/<cycle>/<pass>/ (reports) with root=output/."""
        root = root or self._input_dir
        folder = root / p["cycle"] / p["id"]
        legacy = self._data_dir / root.name / p["cycle"] / p["id"]
        if self._test_mode() and not folder.exists() and legacy.is_dir():
            # ponytail: a test pass of before test/input, test/output (2026-11-19) kept its folders in ./input,
            # ./output: moved on first use. Delete once every deployment resumed or abandoned its old test passes.
            folder.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(legacy, folder)
        return folder

    def _kept_file(self, p: dict, name: str, couple: str) -> Path:
        """config.json is kept per disease, external_data.csv per org unit level (fkt or csb)."""
        return self._pass_dir(p) / _KEPT_INPUTS[self._input_item(name, couple)]

    def _report_path(self, p: dict, couple: str) -> Path:
        return self._pass_dir(p, self._output_dir) / f"report_{couple.replace('/', '_')}.html"

    def _save_work(self, p: dict) -> None:
        """Copies the working files of input/ and output/ into the pass folders (pause, complete)."""
        for root in (self._input_dir, self._output_dir):
            _copy_work(root, self._pass_dir(p, root), _is_cycle, _is_kept)

    def _restore_work(self, p: dict) -> None:
        """Puts the working files saved in the pass folders back into input/ and output/ (resume)."""
        for root in (self._input_dir, self._output_dir):
            _copy_work(self._pass_dir(p, root), root, _is_kept, _is_cycle)

    def _migration_1(self, conn: sqlite3.Connection, uploads: Path) -> None:
        """Passes (2026-10-22), then the move to the pass folders (2026-10-27): uploads/<cycle>/<pass>/ goes to
        input/<cycle>/<pass>/ and the reports to output/<cycle>/<pass>/. Without an active pass, the working files of
        input/ and output/ are copied into the last paused pass (with an active pass they are its own: they stay where
        they are). Any other paused pass with an open run, or one whose files another run emptied since, will fetch
        again: its run is reset. The emptied uploads/ folders are left.
        """
        _migrate_to_passes(conn, uploads)
        conn.executescript(_SCHEMA)  # the tables added before the migrations were numbered
        for p in self._passes(conn):
            for f in sorted((uploads / p["cycle"] / p["id"]).glob("*")):
                folder = self._pass_dir(p, self._output_dir if f.name.startswith("report_") else None)
                folder.mkdir(parents=True, exist_ok=True)
                shutil.move(f, folder / f.name)
        paused = self._passes(conn, "state = 'paused'")
        owner = None if self._active(conn) else next(reversed(paused), None)
        if owner:
            self._save_work(owner)
        for p in paused:
            run = self._open_run(conn, p["id"])
            if run and (p is not owner or conn.execute("SELECT 1 FROM forecast_runs WHERE opened_at > ?",
                                                       (run["opened_at"],)).fetchone()):
                self._reset(conn, p, list(run_items(run["couple"])), "pass_folders")

    def _migration_2(self, conn: sqlite3.Connection, uploads: Path) -> None:
        """FOREIGN KEY pass_id -> passes(id) on the 4 tables that carry it (2026-11-18, foreign-keys.md).

        SQLite cannot add a constraint to a table: each one is renamed, created again from _SCHEMA and filled back
        (migrate() keeps foreign_keys off, as SQLite's table rebuild procedure asks). A row whose pass does not exist
        fails the migration: nothing changes. forecast_runs.external_data (dbs from before 2026-10-12, unused) is dropped.
        """
        tables = ("checkpoints", "forecast_runs", "pipeline_events", "availability_checks")
        for (index,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL"
                                     f" AND tbl_name IN ({', '.join('?' * len(tables))})", tables).fetchall():
            conn.execute(f"DROP INDEX {index}")  # _SCHEMA creates them again on the new tables
        for table in tables:
            conn.execute(f"ALTER TABLE {table} RENAME TO {table}_v1")
        # Not executescript: it would commit the caller's transaction. ";\n" ends a statement (comments hold "; ").
        for statement in _SCHEMA.split(";\n"):
            conn.execute(statement)
        for table in tables:
            columns = ", ".join(r[1] for r in conn.execute(f"PRAGMA table_info({table})"))
            conn.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_v1")
            conn.execute(f"DROP TABLE {table}_v1")
        if orphans := conn.execute("PRAGMA foreign_key_check").fetchall():
            raise sqlite3.IntegrityError(
                f"{len(orphans)} row(s) refer to a pass that does not exist (table, rowid): "
                f"{[(t, rowid) for t, rowid, *_ in orphans[:10]]}; fix them, then run python -m etlhub.migrate again")

    def _migration_3(self, conn: sqlite3.Connection, uploads: Path) -> None:
        """The configuration of a pass, fixed when it starts (2026-11-20, pass-config.md): PASS_CONFIG columns.
        Existing passes get NULL: they keep reading Redis / .env, as before. Migration 1 creates passes from today's
        _PASSES on a db without it: the columns may be there already."""
        present = {r[1] for r in conn.execute("PRAGMA table_info(passes)")}
        # The columns of 2026-11-20, not PASS_CONFIG: what this released migration adds must never change.
        for column in ("gee_variables", "parent_ou", "log_level", "dry_run", "dhis_url"):
            if column not in present:
                conn.execute(f"ALTER TABLE passes ADD COLUMN {column} {'INTEGER' if column == 'dry_run' else 'TEXT'}")

    def _migration_4(self, conn: sqlite3.Connection, uploads: Path) -> None:
        """PIVOT_URL fixed by a pass too (2026-11-27, pass-config.md): passes.pivot_url. Existing passes get NULL: they
        keep reading the editable config (Redis), as before. Present already if migration 1 created passes just now."""
        if "pivot_url" not in {r[1] for r in conn.execute("PRAGMA table_info(passes)")}:
            conn.execute("ALTER TABLE passes ADD COLUMN pivot_url TEXT")

    # Schema migrations (docs/decision-design/db-migrations/db-migrations.md): MIGRATIONS[i] takes a db from version i
    # to i + 1, applied by hand only (migrate()). Never edit a released one: a change to _SCHEMA ships with a new
    # migration and its test on a db of the previous version.
    MIGRATIONS = (_migration_1, _migration_2, _migration_3, _migration_4)

    def _check_schema(self, conn: sqlite3.Connection, where: str) -> None:
        """A new db gets the schema at SCHEMA_VERSION; any other one must already be at it: nothing migrates here."""
        if _schema_version(conn) is None:
            conn.executescript(_SCHEMA)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        elif (version := self._pending(conn, where)) is not None:
            raise _schema_error(where, version)

    def _apply(self, conn: sqlite3.Connection, version: int, uploads: Path) -> None:
        """Every pending migration in one transaction: a failure leaves the db as it was (not the files it moved)."""
        conn.execute("BEGIN IMMEDIATE")
        try:
            for i in range(version, SCHEMA_VERSION):
                self.MIGRATIONS[i](self, conn, uploads)
                conn.execute(f"PRAGMA user_version = {i + 1}")
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise

    def migrate(self, check: bool = False) -> list[str]:
        """Brings etlhub.db and the test-mode db (Redis) to SCHEMA_VERSION, each after a backup next to etlhub.db.

        By hand only (python -m etlhub.migrate), the API and the workers stopped. check=True lists what is pending.
        ponytail: the backup holds the db, not input/ output/ uploads/ that a migration moves; copy them by hand first.
        """
        stamp, done = datetime.now().strftime("%Y%m%dT%H%M%S"), []
        # autocommit=True: an executescript inside a migration does not commit the transaction of _apply.
        if self._db_path.is_file():
            with closing(sqlite3.connect(self._db_path, timeout=5, autocommit=True)) as conn:
                done.append(self._migrate_one(conn, str(self._db_path), self._uploads_root, self._db_path.name, stamp, check))
        with self._blob.lock(), closing(sqlite3.connect(":memory:", autocommit=True)) as conn:
            if data := self._blob.get():
                conn.deserialize(data)
                line = self._migrate_one(conn, _BLOB, self._uploads_root / "dry_run", "test_mode.db", stamp, check)
                if line and not check:
                    self._blob.set(conn.serialize())
                done.append(line)
        return [line for line in done if line]

    def _migrate_one(self, conn: sqlite3.Connection, where: str, uploads: Path, name: str, stamp: str,
                     check: bool) -> str | None:
        """One db: None if nothing is pending, else its line; without check, a backup (VACUUM INTO) then _apply."""
        if (version := self._pending(conn, where)) is None:
            return None
        line = f"{where}: version {version} -> {SCHEMA_VERSION}"
        if check:
            return line
        backup = self._db_path.with_name(f"{name}.v{version}-{stamp}.bak")
        conn.execute("VACUUM INTO ?", (str(backup),))
        self._apply(conn, version, uploads)
        return f"{line}, backup {backup}"

    def check_schema(self) -> None:
        """At API start: no start on a db that needs python -m etlhub.migrate, or one newer than this code."""
        if pending := self.migrate(check=True):
            raise SchemaVersionError("\n".join(pending) + ": stop the workers, then run python -m etlhub.migrate")

    @staticmethod
    def _pending(conn: sqlite3.Connection, where: str) -> int | None:
        """The version of a db to migrate; None if it is new or current. A db newer than this code is refused."""
        version = _schema_version(conn)
        if version is not None and version > SCHEMA_VERSION:
            raise _schema_error(where, version)
        return version if version is not None and version < SCHEMA_VERSION else None

    def _archive_report(self, p: dict, couple: str) -> None:
        """Keeps the report of a closed run: the next run empties output/."""
        report = self._output_dir / "forecast_report.html"
        if report.is_file():
            target = self._report_path(p, couple)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(report, target)

    def report(self, pass_id: str | None, couple: str) -> Path | None:
        """The archived report of a closed run (the pass shown on the Dashboard by default), or None."""
        with self._transaction(read=True) as conn:
            p = self._get_pass(conn, pass_id) if pass_id else self._shown(conn)
        path = p and self._report_path(p, couple)
        return path if path and path.is_file() else None

    def _shown(self, conn: sqlite3.Connection) -> dict | None:
        """The pass the Dashboard shows: the active one, else the last one of the target month."""
        return self._active(conn) or next(reversed(self._passes(conn, "cycle = ?", (self._target(conn),))), None)

    def _clear_workdirs(self) -> None:
        """Empties the working files of input/ and output/ (not the pass folders): a run never reads another's files."""
        for directory in (self._input_dir, self._output_dir):
            _clear(directory, _is_cycle)

    # --- jobs ----------------------------------------------------------------------------

    def default_dry_run(self) -> bool:
        """DRYRUN = TEST MODE (rule of 2026-11-20, applied since 2026-11-23): test mode never writes to DHIS2, production always does.
        Nothing else chooses it: no launch parameter, no Home choice, no .env."""
        return self._test_mode()

    def _config(self, gee_variables: str | None) -> dict:
        """The configuration a new pass fixes (PASS_CONFIG), read now: outside a transaction, never through the store."""
        return {"gee_variables": gee_variables, "dry_run": self.default_dry_run(), **self._live_config()}

    @staticmethod
    def _check_config(p: dict, now: dict) -> None:
        """A launch in pass p runs on its DHIS2, fixed when it started (none fixed before 2026-11-20).
        now: _config() of this launch."""
        dhis_url = now["dhis_url"]
        if p.get("dhis_url") and dhis_url != p["dhis_url"]:
            raise PipelineBlockedError(f"Pass {p['id']} runs on the DHIS2 {p['dhis_url']}, fixed when it started: "
                                       f"log in to it to launch its jobs (session on {dhis_url or 'none'})")

    def start(self, task: str, job_id: str, confirm: bool = False, carry_over: dict[str, dict] | None = None,
              gee_variables: str | None = None) -> None:
        """Takes the lock and marks the checkpoint running. A refusal writes nothing.

        Raises PipelineBlockedError, or ConfirmationRequiredError for an item already in success without confirm.
        A run job resets its dependents in the run and gets the run context (DISEASE_CODE, OU_LEVEL).
        Without an active pass, a launch starts one (confirm=true after a complete pass).
        The launched event keeps the job's DRYRUN, the mode's (DRYRUN = TEST MODE; a launch from a session on another
        DHIS2 than the pass's is refused: _check_config): whether this job may write to DHIS2, and, for an
        import, its parameters (`carry_over[item]`). A launch that starts a pass carries over the imports done before
        in the cycle (`carry_over`: the current parameters of each import; None records and carries nothing).
        gee_variables (import_gee, comma-separated): the choice of its dialog, kept on the pass once the launch is
        accepted (a refusal changes nothing); None keeps the pass's. gee-import.md.
        """
        config = self._config(gee_variables)  # read before the transaction: fixed if this launch starts the pass
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn, confirm, config)
            self._check_config(p, config)
            dry_run = config["dry_run"]  # the mode's: DRYRUN = TEST MODE, whatever the pass stored
            rows = self._rows(conn, p["id"])
            run = self._open_run(conn, p["id"])
            couple = run["couple"] if run else None
            step, item = resolve_slot(task, rows, couple)
            require_confirmation(step, item, rows, confirm)
            if gee_variables is not None:
                conn.execute("UPDATE passes SET gee_variables = ? WHERE id = ?", (gee_variables, p["id"]))
            if p.get("new"):
                self._begin(conn, p)
            self._take_lock(conn, job_id, task)
            self._upsert(conn, p, step, item, job_id, "running")
            self._event(conn, p, "launched", step, item, job_id,
                        {**({"confirm": True} if confirm else {}), "dry_run": dry_run,
                         **({"params": carry_over[item]} if carry_over and item in carry_over else {})})
            if p.get("new") and carry_over:
                self._carry_over(conn, p, carry_over, item, dry_run)
            if step == "forecast":
                self._reset(conn, p, dependents(item), "relaunch", job_id)
                self._apply_context(run_context(couple))  # inside the transaction: a failure writes nothing

    def _begin(self, conn: sqlite3.Connection, p: dict) -> None:
        """A new pass: its folders, empty working files (the previous pass saved or dropped them when it left), and
        the config / external_data uploads of the previous pass of the cycle when it is paused or complete (carried
        as success, like the imports). pass-folders.md. Each mode has its own working files (work_dir, since 2026-11-19).
        """
        self._clear_workdirs()
        for root in (self._input_dir, self._output_dir):
            self._pass_dir(p, root).mkdir(parents=True, exist_ok=True)
        prev = next(reversed(self._passes(conn, "cycle = ? AND id != ?", (p["cycle"], p["id"]))), None)
        if prev is None or prev["state"] not in ("paused", "complete"):
            return
        rows = self._rows(conn, prev["id"])
        for item, file_name in _KEPT_INPUTS.items():
            row, kept = rows.get(("forecast", item)), self._pass_dir(prev) / file_name
            if row and row["status"] == "success" and kept.is_file():
                shutil.copyfile(kept, self._pass_dir(p) / file_name)
                self._carry(conn, p, "forecast", item, {"pass_id": prev["id"], **row}, {})

    def _carry_over(self, conn: sqlite3.Connection, p: dict, params: dict[str, dict], launched: str | None,
                    dry_run: bool) -> None:
        """A new pass: each import whose latest success in another pass of the cycle (any state) was launched with the
        same parameters and DRYRUN as this launch is success at once; approve_imports too, when both its prerequisites are
        carried. The launched item is relaunched, not carried. The operator relaunches a carried item with confirm=true,
        as any success. cycle-passes.md § 11.
        """
        carried = set()
        for item in IMPORT_TASKS:
            prev = self._last_success(conn, p, item) if item != launched and item in params else None
            if prev and prev["launch"].get("dry_run") == dry_run and prev["launch"].get("params") == params[item]:
                self._carry(conn, p, "data_import", item, prev, {"dry_run": dry_run})
                carried.add(item)
        if {"import_pivot_com", "import_pivot_csb"} <= carried and (prev := self._last_success(conn, p, "approve_imports")):
            self._carry(conn, p, "data_import", "approve_imports", prev, {})

    @staticmethod
    def _last_success(conn: sqlite3.Connection, p: dict, item: str) -> dict | None:
        """The latest success of a data_import item in another pass of p's cycle, with its launched event's detail."""
        row = conn.execute(
            "SELECT c.pass_id, c.job_id, c.updated_at FROM checkpoints c JOIN passes s ON s.id = c.pass_id"
            " WHERE s.cycle = ? AND c.pass_id != ? AND c.step = 'data_import' AND c.item = ? AND c.status = 'success'"
            " ORDER BY c.updated_at DESC, s.started_at DESC LIMIT 1", (p["cycle"], p["id"], item)).fetchone()
        if not row:
            return None
        launch = row[1] and conn.execute("SELECT detail FROM pipeline_events WHERE job_id = ? AND event = 'launched'",
                                         (row[1],)).fetchone()
        return {"pass_id": row[0], "job_id": row[1], "updated_at": row[2],
                "launch": json.loads(launch[0]) if launch and launch[0] else {}}

    def _carry(self, conn: sqlite3.Connection, p: dict, step: str, item: str, prev: dict, extra: dict) -> None:
        self._upsert(conn, p, step, item, prev["job_id"], "success")
        self._event(conn, p, "carried_over", step, item, prev["job_id"],
                    {"from_pass": prev["pass_id"], "status": "success", "updated_at": prev["updated_at"], **extra})

    def finish(self, job_id: str, state: str) -> None:
        """Records the final status (success | error) and frees the lock. A post_forecast success closes the run.

        The success that completes an active pass closes it (cycle_closed). A pass paused or abandoned meanwhile
        (lock released) gets the job's end, and stays as it is.
        """
        with self._transaction() as conn:
            row = conn.execute("SELECT step, item FROM checkpoints WHERE job_id = ?", (job_id,)).fetchone()
            conn.execute("UPDATE checkpoints SET status = ?, updated_at = ? WHERE job_id = ?", (state, _now(), job_id))
            self._free_lock(conn, job_id)
            # The launched event, not the checkpoint: a reset may have deleted the job's row before it ended.
            step, item, pass_id = self._launched(conn, job_id) or (*(row or (None, None)), None)
            p = self._pass_of(conn, pass_id)
            self._event(conn, p, "succeeded" if state == "success" else "failed", step, item, job_id)
            if row and state == "success" and row[0] == "forecast" and row[1].endswith(":post_forecast"):
                couple = row[1].split(":")[0]
                conn.execute("UPDATE forecast_runs SET state = 'closed', closed_at = ?"
                             " WHERE state = 'open' AND couple = ? AND pass_id = ?", (_now(), couple, p["id"]))
                self._archive_report(p, couple)
                self._event(conn, p, "run_closed", "forecast", job_id=job_id, detail={"couple": couple})
            if state == "success" and p.get("state") == "active" and progress(self._rows(conn, p["id"]))["current_step"] is None:
                conn.execute("UPDATE passes SET state = 'complete' WHERE id = ?", (p["id"],))
                self._event(conn, p, "cycle_closed", job_id=job_id)
                self._save_work(p)  # a complete pass keeps its folders

    @staticmethod
    def _launched(conn: sqlite3.Connection, job_id: str) -> tuple[str, str, str] | None:
        return conn.execute("SELECT step, item, pass_id FROM pipeline_events WHERE job_id = ? AND event = 'launched'",
                            (job_id,)).fetchone()

    # --- input files -----------------------------------------------------------------------

    def _check_input_change(self, conn: sqlite3.Connection, p: dict, name: str, confirm: bool,
                            removed: bool) -> tuple[str, list[str]]:
        """Checks an upload or delete of config / external_data. Returns (couple, items to reset after it)."""
        rows = self._rows(conn, p["id"])
        run = self._open_run(conn, p["id"])
        if run is None:
            raise PipelineBlockedError(f"Changing {name} needs an open forecast run (POST /pipeline/runs)")
        couple = run["couple"]
        if not removed:
            reason = blocking_reason(rows, "forecast", self._input_item(name, couple), couple)
            if reason:
                raise PipelineBlockedError(reason)
        return couple, require_input_confirmation(name, couple, rows, confirm)

    @staticmethod
    def _input_item(name: str, couple: str) -> str:
        return config_item(couple) if name == "config" else external_data_item(couple)

    @contextmanager
    def change_input(self, name: str, confirm: bool = False, removed: bool = False) -> Iterator[None]:
        """Upload (or delete, removed=True) of config.json / external_data.csv in the open run, under the lock.

        config is the item config/<disease>, shared by the disease's 3 runs; external_data is the item
        external_data/<level>, shared by the runs of its org unit level. The file written in input/ is also kept in
        input/<cycle>/<pass>/ and copied back when another run of the same disease (config) or level (external_data) opens.
        A change resets the open run from validate_inputs on, and needs confirm once that file was used.
        """
        action = "delete" if removed else "upload"
        job_id = f"{action}_{name}_{uuid.uuid4().hex[:8]}"
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn)
            couple, reset = self._check_input_change(conn, p, name, confirm, removed)
            self._take_lock(conn, job_id, f"{action} {name}")
            item = self._input_item(name, couple)
            if not removed:
                self._upsert(conn, p, "forecast", item, job_id, "running")
        try:
            yield
            with self._transaction() as conn:
                if removed:
                    self._delete(conn, p, [item])
                else:
                    self._upsert(conn, p, "forecast", item, job_id, "success")
                self._event(conn, p, "removed" if removed else "uploaded", "forecast", item, job_id,
                            {"confirm": True} if confirm else None)
                self._reset(conn, p, reset, "input_change", job_id)
                self._keep(p, name, couple, removed)
                self._free_lock(conn, job_id)
        except BaseException:  # the change itself or its recording: the lock must not stay taken
            self.finish(job_id, "error")
            raise

    def _keep(self, p: dict, name: str, couple: str, removed: bool) -> None:
        kept = self._kept_file(p, name, couple)
        if removed:
            kept.unlink(missing_ok=True)
            return
        kept.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._input_dir / ("config.json" if name == "config" else "external_data.csv"), kept)

    def launch_cycle(self) -> str:
        """The month of the active pass. PipelineBlockedError without one."""
        with self._transaction(read=True) as conn:
            return self._current(conn)["cycle"]

    def set_cycle(self, cycle: str | None) -> dict:
        """Chooses the month (YYYYMM) the next pass starts on; None or the calendar month = follow the calendar month.

        Refused while a job runs, while another month has an active pass, and for a future month.
        Not journaled: a choice is not pass work (the pass_started of the next launch says who started it).
        """
        with self._transaction() as conn:
            self._check_lock_free(conn)
            month = pipeline.this_month()
            cycle = cycle or month
            if cycle > month:
                raise PipelineBlockedError(f"Cycle {cycle} is in the future: the latest is {month}")
            active = self._active(conn)
            if active and cycle != active["cycle"]:
                raise PipelineBlockedError(f"Pass {active['id']} ({active['cycle']}) is active: pause or abandon it first")
            self._set_target(conn, cycle)
        return {"cycle": cycle}

    # --- passes --------------------------------------------------------------------------------

    def start_pass(self, confirm: bool = False, carry_over: dict[str, dict] | None = None,
                   gee_variables: str | None = None) -> dict:
        """Starts a pass on the target month at once (Home, "New pass"): its folders, and what is carried over from
        the cycle (uploads, and imports with the same parameters `carry_over`). After a complete or paused pass, only
        with confirm=true. Refused while a job runs or a pass is active. pass-folders.md § 6.
        Its configuration is fixed now (PASS_CONFIG): gee_variables (comma-separated; None: all), PARENT_OU, LOG_LEVEL,
        PIVOT_URL and the DHIS2 URL of the last login; dry_run is recorded but the mode decides (DRYRUN = TEST MODE).
        """
        config = self._config(gee_variables)
        with self._transaction() as conn:
            self._check_lock_free(conn)
            if active := self._active(conn):
                raise PipelineBlockedError(f"Pass {active['id']} ({active['cycle']}) is active: pause or abandon it first")
            p = self._current(conn, confirm, config)
            self._begin(conn, p)
            if carry_over:
                self._carry_over(conn, p, carry_over, None, p["dry_run"])
        return {c: p[c] for c in _PASS_COLUMNS}

    def pass_config(self) -> dict | None:
        """The fixed configuration (PASS_CONFIG) of the active pass of the mode served; None without one.
        A launch hands it to its Celery job (tasks.py); script_config._get reads it here outside a Celery job."""
        with self._transaction(read=True) as conn:
            active = self._active(conn)
        return {c: active[c] for c in PASS_CONFIG} if active else None

    def pause(self, cause: str = "manual", reason: str | None = None) -> dict:
        """Pauses the active pass: its checkpoints and open forecast run stay as they are, to resume from the Journal."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn)
            self._set_state(conn, p, "paused", cause, reason=reason)
        return p

    def leave_mode(self, action: str | None) -> dict | None:
        """The user leaves the mode served: its active pass is paused or abandoned (`action`), as they chose; a pass
        lives in one mode. None: no active pass, nothing to do. Without action: ConfirmationRequiredError, nothing done.
        Refused while a job runs, as pause and abandon are."""
        with self._transaction() as conn:
            active = self._active(conn)
        if active is None:
            return None
        mode, other = ("test", "production") if self._test_mode() else ("production", "test")
        if action is None:
            raise ConfirmationRequiredError(
                f"Pass {active['id']} ({active['cycle']}) is active in {mode} mode, and a pass lives in one mode: "
                f"pause it (resume it later in {mode} mode) or abandon it before switching to {other}.",
                {"pass_id": active["id"], "cycle": active["cycle"], "mode": mode, "to": other,
                 "actions": ["pause", "abandon"]})
        reason = f"Mode changed manually by the user: from {mode} to {other}"
        if action == "pause":
            return self.pause("mode_change", reason)
        return self.abandon(active["id"], "mode_change", reason)

    def resume(self, pass_id: str) -> dict:
        """Makes a paused pass of the current mode active again; launches go to its month."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._paused_or_active(conn, pass_id, "resumed", ("paused",))
            active = self._active(conn)
            if active:
                raise PipelineBlockedError(f"Pass {active['id']} ({active['cycle']}) is active: pause or abandon it first")
            self._set_target(conn, p["cycle"])
            self._restore_work(p)
            if run := self._open_run(conn, p["id"]):  # its uploads too (a pass reset by the migration saved nothing)
                self._restore(p, run["couple"], self._rows(conn, p["id"]))
            self._set_state(conn, p, "active", "manual")
        return p

    def abandon(self, pass_id: str, cause: str = "manual", reason: str | None = None) -> dict:
        """Abandons an active or paused pass for good: its open run is abandoned, its files are deleted except the
        reports of its closed runs (its checkpoints and journal stay readable)."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._paused_or_active(conn, pass_id, "abandoned", ("active", "paused"))
            run = self._open_run(conn, p["id"])
            if run:
                conn.execute("UPDATE forecast_runs SET state = 'abandoned', closed_at = ? WHERE state = 'open' AND pass_id = ?",
                             (_now(), p["id"]))
                self._event(conn, p, "run_abandoned", "forecast", detail={"couple": run["couple"], "by": "pass_abandoned"})
            if p["state"] == "active":  # the working files are its own
                self._clear_workdirs()
            self._set_state(conn, p, "abandoned", cause, reason=reason)
            shutil.rmtree(self._pass_dir(p), ignore_errors=True)
            _clear(self._pass_dir(p, self._output_dir), _is_kept)
        return p

    def _paused_or_active(self, conn: sqlite3.Connection, pass_id: str, action: str, states: tuple[str, ...]) -> dict:
        p = self._get_pass(conn, pass_id)
        if p is None:
            mode = "test" if self._test_mode() else "production"
            raise PipelineBlockedError(f"No pass {pass_id} in {mode} mode: a test pass is {action} in test mode, "
                                       "a production pass in production")
        if p["state"] not in states:
            raise PipelineBlockedError(f"Pass {pass_id} is {p['state']}: it cannot be {action}")
        return p

    # --- forecast runs (R6) ---------------------------------------------------------------

    def open_run(self, couple: str, confirm: bool = False) -> dict:
        """Opens the forecast run of a couple: one at a time, step data_import done, input/ and output/ emptied.

        Reopening a couple already closed in the pass needs confirm and resets all its items.
        """
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn)
            rows = self._rows(conn, p["id"])
            if "forecast" not in accessible_steps(rows):
                raise PipelineBlockedError("Opening a forecast run needs step data_import done first")
            current = self._open_run(conn, p["id"])
            if current:
                raise PipelineBlockedError(f"Run {current['couple']} is open: finish or abandon it first")
            items = list(run_items(couple))
            closed = conn.execute("SELECT 1 FROM forecast_runs WHERE pass_id = ? AND couple = ? AND state = 'closed'",
                                  (p["id"], couple)).fetchone()
            if closed and not confirm:
                raise ConfirmationRequiredError(
                    f"Run {couple} is already closed in cycle {p['cycle']}: resend with confirm=true to reopen it",
                    impact("forecast", couple, rows, items))
            self._reset(conn, p, items, "reopen")
            context = run_context(couple)
            self._clear_workdirs()  # inside the transaction: if it fails, the run is not opened
            self._restore(p, couple, rows)
            run = {"pass_id": p["id"], "couple": couple, "state": "open", "disease_code": context["DISEASE_CODE"],
                   "ou_level": context["OU_LEVEL"], "alert_name": context["ALERT_NAME"], "opened_at": _now_us()}
            conn.execute(f"INSERT INTO forecast_runs ({', '.join(_RUN_COLUMNS)})"
                         f" VALUES ({', '.join('?' * len(_RUN_COLUMNS))})", tuple(run[c] for c in _RUN_COLUMNS))
            self._event(conn, p, "run_opened", "forecast", detail={"couple": couple, **({"confirm": True} if confirm else {})})
        return run

    def _restore(self, p: dict, couple: str, rows: pipeline.Rows) -> None:
        """Copies the disease's config and the level's external_data, uploaded earlier in the pass, into input/."""
        for name, file_name in (("config", "config.json"), ("external_data", "external_data.csv")):
            kept = self._kept_file(p, name, couple)
            if kept.is_file() and status(rows, "forecast", self._input_item(name, couple)) == "success":
                self._input_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(kept, self._input_dir / file_name)

    def abandon_run(self) -> str:
        """Abandons the open run: nothing is published, its items go back to pending. Returns the couple."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn)
            run = self._open_run(conn, p["id"])
            if run is None:
                raise PipelineBlockedError("No forecast run is open")
            conn.execute("UPDATE forecast_runs SET state = 'abandoned', closed_at = ? WHERE state = 'open' AND pass_id = ?",
                         (_now(), p["id"]))
            self._event(conn, p, "run_abandoned", "forecast", detail={"couple": run["couple"], "by": "manual"})
            self._reset(conn, p, list(run_items(run["couple"])), "abandon")
        return run["couple"]

    def decide(self, decision: str) -> str:
        """Approval of the open run's forecast: approve unlocks post_forecast, reject resets the forecast."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn)
            rows = self._rows(conn, p["id"])
            run = self._open_run(conn, p["id"])
            if run is None:
                raise PipelineBlockedError("No forecast run is open")
            couple = run["couple"]
            if decision == "approve":
                reason = blocking_reason(rows, "forecast", f"{couple}:approve", couple)
                if reason:
                    raise PipelineBlockedError(reason)
                self._upsert(conn, p, "forecast", f"{couple}:approve", None, "success")
            else:
                forecast = f"{couple}:forecast"
                if status(rows, "forecast", forecast) != "success":
                    raise PipelineBlockedError(f"Nothing to reject: {forecast} is not in success")
            self._event(conn, p, "decided", "forecast", f"{couple}:approve", detail={"decision": decision})
            if decision != "approve":
                self._reset(conn, p, [forecast, *dependents(forecast)], "reject")
        return couple

    def skip_alerts(self) -> str:
        """Marks the open CSB run's calc_orgunit_alerts as success without running anything.

        Kept beside the job since 2026-11-24 (owner: launch it, "not only skip"): the CSB alerts are then not
        computed, and post_forecast posts no alerts.json.
        """
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn)
            run = self._open_run(conn, p["id"])
            if run is None:
                raise PipelineBlockedError("No forecast run is open")
            couple, item = run["couple"], f"{run['couple']}:calc_orgunit_alerts"
            if item not in run_items(couple):
                raise PipelineBlockedError(f"{couple} has no calc_orgunit_alerts (CSB runs only)")
            reason = blocking_reason(self._rows(conn, p["id"]), "forecast", item, couple)
            if reason:
                raise PipelineBlockedError(reason)
            self._upsert(conn, p, "forecast", item, None, "success")
            self._event(conn, p, "skipped", "forecast", item)
        return couple

    def decide_imports(self, decision: str) -> None:
        """approve_imports (step data_import): approve unlocks build_analytics, reject sends it back to pending.

        The user checks the COM and CSB case counts of the imports before approving.
        """
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn)
            rows = self._rows(conn, p["id"])
            if decision == "approve":
                reason = blocking_reason(rows, "data_import", "approve_imports")
                if reason:
                    raise PipelineBlockedError(reason)
                self._upsert(conn, p, "data_import", "approve_imports", None, "success")
            else:
                conn.execute("DELETE FROM checkpoints WHERE pass_id = ? AND step = 'data_import' AND item = 'approve_imports'",
                             (p["id"],))
            self._event(conn, p, "decided", "data_import", "approve_imports", detail={"decision": decision})

    def reusable_availability(self, params: dict[str, str]) -> dict[str, dict]:
        """Per task, the latest stored check of the shown cycle (any pass) that still holds: same params, at most
        30 days old, no launch of that import in the cycle since it started, and no build_analytics succeeded since (the
        analytics part of every section may have changed). Tasks without one are left out.

        {task: {"section", "checked_at", "checked_by", "pass_id", "last_analytics"}}.
        """
        cutoff = (datetime.now() - timedelta(days=_AVAILABILITY_DAYS)).isoformat(timespec="microseconds")
        found = {}
        with self._transaction(read=True) as conn:
            cycle = (self._shown(conn) or {"cycle": self._target(conn)})["cycle"]
            for task, task_params in params.items():
                row = conn.execute(
                    "SELECT section, checked_at, checked_by, pass_id, last_analytics FROM availability_checks c"
                    " WHERE cycle = ? AND task = ? AND params = ? AND checked_at >= ?"
                    " AND NOT EXISTS (SELECT 1 FROM pipeline_events e WHERE e.cycle = c.cycle AND e.at > c.checked_at"
                    " AND ((e.item = c.task AND e.event = 'launched')"
                    " OR (e.item = 'build_analytics' AND e.event = 'succeeded')))"
                    " ORDER BY checked_at DESC LIMIT 1", (cycle, task, task_params, cutoff)).fetchone()
                if row:
                    found[task] = {"section": json.loads(row[0]),
                                   **dict(zip(("checked_at", "checked_by", "pass_id", "last_analytics"), row[1:]))}
        return found

    def record_availability_check(self, event: str, detail: dict, sections: list[dict] = (),
                                  started_at: str | None = None) -> dict:
        """Journals a GET /import_availability (read only: no lock, no checkpoint) in the pass the Dashboard shows,
        and stores the sections it checked ({task, params, section, last_analytics}) for the other users of the cycle.

        Before the month's first launch there is no pass: event and sections keep pass_id null (the event then shows
        in no journal, like mode_changed). Stored checks older than 30 days are dropped.
        Returns {checked_at: started_at, checked_by, pass_id}.
        """
        cutoff = (datetime.now() - timedelta(days=_AVAILABILITY_DAYS)).isoformat(timespec="microseconds")
        with self._transaction() as conn:
            p = self._shown(conn) or {"id": None, "cycle": self._target(conn)}
            for s in sections:
                conn.execute(
                    "INSERT INTO availability_checks (cycle, pass_id, task, params, checked_at, checked_by, section,"
                    " last_analytics) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (p["cycle"], p["id"], s["task"], s["params"], started_at, _actor(), json.dumps(s["section"]),
                     s["last_analytics"]))
            conn.execute("DELETE FROM availability_checks WHERE checked_at < ?", (cutoff,))
            self._event(conn, p, event, "data_import", detail=detail)
        return {"checked_at": started_at, "checked_by": _actor(), "pass_id": p["id"]}

    # --- reading and unlocking ------------------------------------------------------------

    def progress(self, pass_id: str | None = None) -> dict:
        """State of a pass in the current mode (test or production): by default the active one, else the last one of
        the target month (`pass` null when that month has none yet: the first launch starts it)."""
        with self._transaction(read=True) as conn:
            p = self._get_pass(conn, pass_id) if pass_id else self._shown(conn)
            rows = self._rows(conn, p["id"]) if p else {}
            run = self._open_run(conn, p["id"]) if p else None
            cycle = p["cycle"] if p else self._target(conn)
            lock = self._lock(conn)
        state = progress(rows, run["couple"] if run else None)
        state["cycle"] = cycle
        state["pass"] = p
        state["run"] = run
        state["lock"] = lock
        state["test_mode"] = self._test_mode()
        state["dry_run"] = self.default_dry_run()  # DRYRUN = TEST MODE: every job of this mode
        return state

    # --- lock -------------------------------------------------------------------------------

    def held_lock(self) -> dict | None:
        """The job holding the lock, both modes': {job_id, task, own}. For the unlock route only, which asks the workers
        about that job; one of the other mode (own false) is never shown (progress and messages say so, no more)."""
        with self._transaction(read=True) as conn:
            row = conn.execute(f"SELECT job_id, task FROM {self._lock_table(conn)}").fetchone()
            return {"job_id": row[0], "task": row[1], "own": self._owns(conn, row[0])} if row else None

    def release_lock(self, job_id: str | None = None) -> str | None:
        """Manual unlock (killed worker), from either mode: the lock is both modes'. Returns the freed job_id.

        The job's running checkpoint becomes error and lock_released is journaled in the job's own mode. With job_id,
        only if that job still holds the lock: the one the user was asked about, not a newer one."""
        with self._transaction() as conn:
            row = conn.execute(f"SELECT job_id, task FROM {self._lock_table(conn)}").fetchone()
            if not row or job_id not in (None, row[0]):
                return None
            mine = self._owns(conn, row[0])
        test_mode = self._test_mode() if mine else not self._test_mode()  # a lock without trace: freed as the other's
        with self._mode_transaction(test_mode) as conn:
            if not conn.execute(f"SELECT 1 FROM {self._lock_table(conn)} WHERE job_id = ?", (row[0],)).fetchone():
                return None  # ended meanwhile
            conn.execute("UPDATE checkpoints SET status = 'error', updated_at = ?"
                         " WHERE job_id = ? AND status = 'running'", (_now(), row[0]))
            self._free_lock(conn, row[0])
            step, item, pass_id = self._launched(conn, row[0]) or (None, None, None)
            self._event(conn, self._pass_of(conn, pass_id), "lock_released", step, item, row[0], {"task": row[1]})
        return row[0]

    # --- journal ------------------------------------------------------------------------------

    def _mode_journal(self) -> tuple[str, Callable[[], AbstractContextManager[sqlite3.Connection | None]]]:
        """The current mode and its store: production (SQLite file) or test (Redis blob). A mode never reads the other's."""
        return ("test", self._test_journal) if self._test_mode() else ("production", lambda: self._file_transaction(read=True))

    def current_mode(self) -> str:
        """The current mode: 'production' or 'test' (TEST_MODE)."""
        return self._mode_journal()[0]

    def has_job(self, job_id: str) -> bool:
        """Whether the pipeline of the current mode launched this job (its journal names it): never one of the other mode."""
        _, store = self._mode_journal()
        with store() as conn:
            return bool(conn and conn.execute("SELECT 1 FROM pipeline_events WHERE job_id = ? LIMIT 1", (job_id,)).fetchone())

    def journal(self, pass_id: str) -> list[dict]:
        """Events of a pass of the current mode, oldest first; [] for a pass of the other mode, as for an unknown one."""
        mode, store = self._mode_journal()
        with store() as conn:
            return self._events(conn, pass_id, mode) if conn else []

    def cycles(self) -> list[dict]:
        """Every month with passes of the current mode (and the target month), newest first; each with its passes, newest first.

        A pass: id, cycle, state, started_at, started_by, mode, events and last_at (mode_changed and
        the availability_* reads left out of both: they measure the pipeline's work, not mode switches or reads).
        """
        count = ("SELECT pass_id, count(*), max(at) FROM pipeline_events"
                 " WHERE event NOT IN ('mode_changed', 'availability_checked', 'availability_reused')"
                 " AND pass_id IS NOT NULL GROUP BY pass_id")
        mode, store = self._mode_journal()
        with store() as conn:
            stats = {p: (n, at) for p, n, at in conn.execute(count)} if conn else {}
            passes = [{**p, "mode": mode, **dict(zip(("events", "last_at"), stats.get(p["id"], (0, None))))}
                      for p in (self._passes(conn) if conn else [])]
        with self._transaction(read=True) as conn:
            target = self._target(conn)
        return [{"cycle": c, "target": c == target,
                 "passes": sorted((p for p in passes if p["cycle"] == c), key=lambda p: p["started_at"], reverse=True)}
                for c in sorted({p["cycle"] for p in passes} | {target}, reverse=True)]

    @contextmanager
    def _test_journal(self) -> Iterator[sqlite3.Connection | None]:
        """The test-mode db kept in Redis, or None once Redis no longer has it.

        ponytail: read through a transaction, which saves the blob back (migrated once); a read-only copy if that costs.
        """
        if not self._blob.get():  # Redis down: no session either (401 before this)
            yield None
            return
        with self._memory_transaction() as conn:
            yield conn

    @staticmethod
    def _events(conn: sqlite3.Connection, pass_id: str, mode: str) -> list[dict]:
        rows = conn.execute(f"SELECT {', '.join(_EVENT_COLUMNS)} FROM pipeline_events WHERE pass_id = ? ORDER BY id",
                            (pass_id,)).fetchall()
        return [{**dict(zip(_EVENT_COLUMNS, r)), "detail": json.loads(r[-1]) if r[-1] else None, "mode": mode}
                for r in rows]


SCHEMA_VERSION = len(CheckpointStore.MIGRATIONS)
_BLOB = f"the test-mode db (Redis {RedisBlob.KEY})"


@lru_cache
def get_checkpoint_store() -> CheckpointStore:
    return CheckpointStore()
