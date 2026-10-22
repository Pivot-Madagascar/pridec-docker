import base64
import json
import logging
import shutil
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path

from etlhub.core.config import get_settings
from etlhub.core.request_context import request_context
from etlhub.domain import pipeline
from etlhub.domain.exceptions import ConfirmationRequiredError, ETLException, PipelineBlockedError
from etlhub.domain.pipeline import (
    accessible_steps, blocking_reason, config_item, dependents, disease_of, external_data_item,
    impact, level_of, progress, require_confirmation, require_input_confirmation, resolve_slot, run_context,
    run_items, status,
)
from etlhub.infrastructure.config_store import ConfigStore
from etlhub.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

_checkpoint_store = None
_lock = threading.Lock()

# Same db as request_log, but no retention: a cycle must stay readable.
# A pass is one run of a cycle (month): its checkpoints, forecast runs and journal events carry its id
# (etlhub/docs/decision-design/cycle-passes/cycle-passes.md).
_PASSES = """CREATE TABLE IF NOT EXISTS passes (
    id         TEXT PRIMARY KEY,
    cycle      TEXT NOT NULL,
    state      TEXT NOT NULL,  -- active | paused | complete | abandoned
    started_at TEXT NOT NULL,
    started_by TEXT
)"""
_SCHEMA = _PASSES + """;
CREATE UNIQUE INDEX IF NOT EXISTS one_active_pass ON passes(state) WHERE state = 'active';
CREATE TABLE IF NOT EXISTS checkpoints (
    pass_id    TEXT NOT NULL,
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
    pass_id       TEXT NOT NULL,
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
    pass_id    TEXT  -- NULL: a mode_changed with no active pass
);
CREATE INDEX IF NOT EXISTS ix_pipeline_events_pass ON pipeline_events(pass_id, id);
CREATE INDEX IF NOT EXISTS ix_pipeline_events_job_id ON pipeline_events(job_id);
"""
# Databases created before 2026-10-12 also have an external_data column (DEFAULT 'none'): unused, inserts skip it.
_RUN_COLUMNS = ("pass_id", "couple", "state", "disease_code", "ou_level", "alert_name", "opened_at")
_EVENT_COLUMNS = ("cycle", "pass_id", "at", "step", "item", "event", "job_id", "actor", "request_id", "detail")
_PASS_COLUMNS = ("id", "cycle", "state", "started_at", "started_by")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _now_us() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def _actor(actor: str | None = None) -> str | None:
    """Who acts: the given actor, else the logged-in user of the HTTP request, else the worker."""
    context = request_context.get()
    return actor or (context.get("actor") if context is not None else "worker")


def _migrate_to_passes(conn: sqlite3.Connection, uploads: Path) -> None:
    """One-time migration of a store keyed by month to passes (2026-10-22): the journal of a month is cut after each
    cycle_closed; its checkpoints and kept files go to its last pass, each forecast run to the pass it was opened in.

    ponytail: delete once every store (etlhub.db, the test blob) ran it.
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


def apply_to_config_store(context: dict[str, str | None]) -> None:
    """Writes the run context where the ETL scripts read it (etl/scripts/config.py reads Redis first)."""
    store = ConfigStore()
    written = store.set_all({k: v for k, v in context.items() if v is not None})
    cleared = store.delete_keys([k for k, v in context.items() if v is None])
    if not (written and cleared):
        raise ETLException("Could not write the forecast run context (DISEASE_CODE, OU_LEVEL) to Redis")


TEST_MODE_KEY = "pipeline:test_mode"


def dry_run_enabled() -> bool:
    """DRYRUN as the ETL scripts read it: Redis, loaded from .env at each API start (main.py lifespan), default true."""
    from etl.scripts.config import get_dry_run
    return get_dry_run()


def test_mode_enabled() -> bool:
    """TEST_MODE: etlhub's own test mode (Redis), switched by PUT /pipeline/mode only. Independent of DRYRUN.

    ponytail: one-time migration from the days DRYRUN was also the test mode: the first read starts in the mode DRYRUN
    gives. DRYRUN stays in Redis (the API reloads it from .env at each start). Delete once every deployment ran it.
    """
    value = get_redis().get(TEST_MODE_KEY)
    if value is None:
        value = "true" if dry_run_enabled() else "false"
        get_redis().set(TEST_MODE_KEY, value, nx=True)
    return value == "true"


def write_test_mode(value: bool) -> None:
    get_redis().set(TEST_MODE_KEY, "true" if value else "false")


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
                 test_mode: Callable[[], bool] = test_mode_enabled, set_test_mode: Callable[[bool], None] = write_test_mode,
                 dry_run: Callable[[], bool] = dry_run_enabled,
                 blob: RedisBlob | None = None):
        """In test mode (TEST_MODE) everything is kept in Redis (`blob`), never in the SQLite file.

        The Redis keys and the uploads folder keep their dry_run names: they hold the test state of before TEST_MODE.
        """
        settings = get_settings()
        self._test_mode, self._set_test_mode, self._dry_run = test_mode, set_test_mode, dry_run
        self._blob = blob or RedisBlob()
        self._db_path = Path(db_path or Path(settings.logs_dir) / "etlhub.db")
        data_dir = Path(data_dir or settings.data_dir)
        self._input_dir, self._output_dir = data_dir / "input", data_dir / "output"
        # Uploaded files kept per cycle: input/ is emptied at each run, these are copied back into it.
        self._uploads_root = data_dir / "uploads"
        self._apply_context = apply_context

    # --- helpers (inside a transaction) ---------------------------------------------------

    @property
    def _uploads_dir(self) -> Path:
        return self._uploads_root / "dry_run" if self._test_mode() else self._uploads_root

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Same SQL in both modes: the SQLite file in production, an in-memory copy kept in Redis in test mode."""
        transaction = self._memory_transaction if self._test_mode() else self._file_transaction
        with transaction() as conn:
            yield conn

    @contextmanager
    def _memory_transaction(self) -> Iterator[sqlite3.Connection]:
        with self._blob.lock(), closing(sqlite3.connect(":memory:", isolation_level=None)) as conn:
            data = self._blob.get()
            if data:
                conn.deserialize(data)
            _migrate_to_passes(conn, self._uploads_root / "dry_run")  # a failure saves nothing: the blob is set at the end
            conn.executescript(_SCHEMA)
            conn.execute("BEGIN")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            self._blob.set(conn.serialize())

    @contextmanager
    def _file_transaction(self) -> Iterator[sqlite3.Connection]:
        # BEGIN IMMEDIATE takes the write lock up front: two launches cannot both see the lock free.
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._db_path, timeout=5, isolation_level=None)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("BEGIN IMMEDIATE")  # DDL is transactional in SQLite: a failed migration leaves the file as it was
            try:
                _migrate_to_passes(conn, self._uploads_root)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.executescript(_SCHEMA)
            conn.execute("BEGIN IMMEDIATE")
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

    @staticmethod
    def _passes(conn: sqlite3.Connection, where: str = "1", params: tuple = ()) -> list[dict]:
        """Passes, oldest first."""
        return [dict(zip(_PASS_COLUMNS, r)) for r in conn.execute(
            f"SELECT {', '.join(_PASS_COLUMNS)} FROM passes WHERE {where} ORDER BY started_at", params)]

    def _get_pass(self, conn: sqlite3.Connection, pass_id: str | None) -> dict | None:
        return next(iter(self._passes(conn, "id = ?", (pass_id,))), None)

    def _active(self, conn: sqlite3.Connection) -> dict | None:
        return next(iter(self._passes(conn, "state = 'active'")), None)

    def _pass_of(self, conn: sqlite3.Connection, pass_id: str | None) -> dict:
        """The pass of a job (its launched event), else the active one, else the target month without a pass."""
        return self._get_pass(conn, pass_id) or self._active(conn) or {"id": None, "cycle": self._target(conn)}

    def _set_state(self, conn: sqlite3.Connection, p: dict, state: str, cause: str, actor: str | None = None) -> None:
        conn.execute("UPDATE passes SET state = ? WHERE id = ?", (state, p["id"]))
        p["state"] = state
        self._event(conn, p, "resumed" if state == "active" else state, detail={"cause": cause}, actor=actor)

    def _settle(self, conn: sqlite3.Connection) -> None:
        """The calendar moved on: the active pass that followed it is paused (a pass on a chosen month stays active)."""
        active = self._active(conn)
        if active and active["cycle"] != self._target(conn):
            self._set_state(conn, active, "paused", "month_change", actor="system")

    def _current(self, conn: sqlite3.Connection, confirm: bool | None = None) -> dict:
        """The active pass, which every write goes to. Raises PipelineBlockedError without one.

        A launch (confirm not None) starts a pass on the target month when it has no paused one;
        after a complete pass, only with confirm=true (ConfirmationRequiredError otherwise).
        """
        self._settle(conn)
        active = self._active(conn)
        if active:
            return active
        cycle = self._target(conn)
        last = next(reversed(self._passes(conn, "cycle = ?", (cycle,))), None)
        if last and last["state"] == "paused":
            raise PipelineBlockedError(f"Pass {last['id']} of cycle {cycle} is paused: resume it from the Journal, "
                                       "or choose another cycle")
        if confirm is None:
            raise PipelineBlockedError(f"No active pass in cycle {cycle}: launch a job of step data_import to start one")
        redo = last is not None and last["state"] == "complete"
        if redo and not confirm:
            raise ConfirmationRequiredError(
                f"Cycle {cycle} is complete: resend with confirm=true to start a new pass (the complete one is kept)",
                {"cycle": cycle, "complete_pass": last["id"]})
        p = {"id": uuid.uuid4().hex[:8], "cycle": cycle, "state": "active", "started_at": _now_us(),
             "started_by": _actor()}
        conn.execute(f"INSERT INTO passes ({', '.join(_PASS_COLUMNS)}) VALUES ({', '.join('?' * len(_PASS_COLUMNS))})",
                     tuple(p[c] for c in _PASS_COLUMNS))
        self._event(conn, p, "pass_started", detail={"cause": "redo"} if redo else None)
        return p

    @staticmethod
    def _open_run(conn: sqlite3.Connection, pass_id: str | None) -> dict | None:
        row = conn.execute(f"SELECT {', '.join(_RUN_COLUMNS)} FROM forecast_runs WHERE state = 'open' AND pass_id = ?",
                           (pass_id,)).fetchone()
        return dict(zip(_RUN_COLUMNS, row)) if row else None

    @staticmethod
    def _check_lock_free(conn: sqlite3.Connection) -> None:
        # The lock never expires: a killed worker keeps it until DELETE /pipeline/lock.
        row = conn.execute("SELECT job_id, task, acquired_at FROM pipeline_lock").fetchone()
        if row:
            raise PipelineBlockedError(f"{row[1]} ({row[0]}) is running since {row[2]}: one job at a time")

    @staticmethod
    def _take_lock(conn: sqlite3.Connection, job_id: str, task: str) -> None:
        conn.execute("INSERT INTO pipeline_lock (id, job_id, task, acquired_at) VALUES (1, ?, ?, ?)",
                     (job_id, task, _now()))

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

    def _pass_dir(self, p: dict) -> Path:
        """Files kept per pass: uploads/<cycle>/<pass>/ (uploads/dry_run/… in test mode)."""
        return self._uploads_dir / p["cycle"] / p["id"]

    def _kept_file(self, p: dict, name: str, couple: str) -> Path:
        """config.json is kept per disease, external_data.csv per org unit level (fkt or csb)."""
        key = f"config_{disease_of(couple)}.json" if name == "config" else f"external_data_{level_of(couple)}.csv"
        return self._pass_dir(p) / key

    def _report_path(self, p: dict, couple: str) -> Path:
        return self._pass_dir(p) / f"report_{couple.replace('/', '_')}.html"

    def _archive_report(self, p: dict, couple: str) -> None:
        """Keeps the report of a closed run: the next run empties output/."""
        report = self._output_dir / "forecast_report.html"
        if report.is_file():
            target = self._report_path(p, couple)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(report, target)

    def report(self, pass_id: str | None, couple: str) -> Path | None:
        """The archived report of a closed run (the pass shown on the Dashboard by default), or None."""
        with self._transaction() as conn:
            p = self._get_pass(conn, pass_id) if pass_id else self._shown(conn)
        path = p and self._report_path(p, couple)
        return path if path and path.is_file() else None

    def _shown(self, conn: sqlite3.Connection) -> dict | None:
        """The pass the Dashboard shows: the active one, else the last one of the target month."""
        return self._active(conn) or next(reversed(self._passes(conn, "cycle = ?", (self._target(conn),))), None)

    def _clear_workdirs(self) -> None:
        """Empties input/ and output/ so that a run never reads another couple's files."""
        for directory in (self._input_dir, self._output_dir):
            if not directory.is_dir():
                continue
            for path in directory.iterdir():
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink()

    # --- jobs ----------------------------------------------------------------------------

    def start(self, task: str, job_id: str, confirm: bool = False) -> None:
        """Takes the lock and marks the checkpoint running. A refusal writes nothing.

        Raises PipelineBlockedError, or ConfirmationRequiredError for an item already in success without confirm.
        A run job resets its dependents in the run and gets the run context (DISEASE_CODE, OU_LEVEL).
        Without an active pass, a launch starts one (confirm=true after a complete pass).
        """
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn, confirm)
            rows = self._rows(conn, p["id"])
            run = self._open_run(conn, p["id"])
            couple = run["couple"] if run else None
            step, item = resolve_slot(task, rows, couple)
            require_confirmation(step, item, rows, confirm)
            self._take_lock(conn, job_id, task)
            self._upsert(conn, p, step, item, job_id, "running")
            self._event(conn, p, "launched", step, item, job_id, {"confirm": True} if confirm else None)
            if step == "forecast":
                self._reset(conn, p, dependents(item), "relaunch", job_id)
                self._apply_context(run_context(couple))  # inside the transaction: a failure writes nothing

    def finish(self, job_id: str, state: str) -> None:
        """Records the final status (success | error) and frees the lock. A post_forecast success closes the run.

        The success that completes an active pass closes it (cycle_closed). A pass paused or abandoned meanwhile
        (lock released) gets the job's end, and stays as it is.
        """
        with self._transaction() as conn:
            row = conn.execute("SELECT step, item FROM checkpoints WHERE job_id = ?", (job_id,)).fetchone()
            conn.execute("UPDATE checkpoints SET status = ?, updated_at = ? WHERE job_id = ?", (state, _now(), job_id))
            conn.execute("DELETE FROM pipeline_lock WHERE job_id = ?", (job_id,))
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

    @staticmethod
    def _launched(conn: sqlite3.Connection, job_id: str) -> tuple[str, str, str] | None:
        return conn.execute("SELECT step, item, pass_id FROM pipeline_events WHERE job_id = ? AND event = 'launched'",
                            (job_id,)).fetchone()

    @contextmanager
    def run(self, task: str, job_id: str, confirm: bool = False) -> Iterator[None]:
        """For synchronous work: start, then success or error when the block ends."""
        self.start(task, job_id, confirm)
        try:
            yield
        except BaseException:
            self.finish(job_id, "error")
            raise
        self.finish(job_id, "success")

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
        uploads/<cycle>/<pass>/ and copied back when another run of the same disease (config) or level (external_data) opens.
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
                conn.execute("DELETE FROM pipeline_lock WHERE job_id = ?", (job_id,))
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
        with self._transaction() as conn:
            return self._current(conn)["cycle"]

    def set_cycle(self, cycle: str | None) -> dict:
        """Chooses the month (YYYYMM) the next pass starts on; None or the calendar month = follow the calendar month.

        Refused while a job runs, while another month has an active pass, and for a future month.
        Not journaled: a choice is not pass work (the pass_started of the next launch says who started it).
        """
        with self._transaction() as conn:
            self._check_lock_free(conn)
            self._settle(conn)
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

    def pause(self) -> dict:
        """Pauses the active pass: its checkpoints and open forecast run stay as they are, to resume from the Journal."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            p = self._current(conn)
            self._set_state(conn, p, "paused", "manual")
        return p

    def resume(self, pass_id: str) -> dict:
        """Makes a paused pass of the current mode active again; launches go to its month."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            self._settle(conn)
            p = self._paused_or_active(conn, pass_id, "resumed", ("paused",))
            active = self._active(conn)
            if active:
                raise PipelineBlockedError(f"Pass {active['id']} ({active['cycle']}) is active: pause or abandon it first")
            self._set_target(conn, p["cycle"])
            self._set_state(conn, p, "active", "manual")
            run = self._open_run(conn, p["id"])
            later = run and conn.execute("SELECT 1 FROM forecast_runs WHERE opened_at > ?", (run["opened_at"],)).fetchone()
            # ponytail: only runs of this mode are seen; test and production share input/ and output/ (known limit).
            if later:  # another run emptied input/ and output/ meanwhile: what the open run fetched is gone
                self._reset(conn, p, list(run_items(run["couple"])), "resume")
                self._clear_workdirs()
                self._restore(p, run["couple"], self._rows(conn, p["id"]))
        return p

    def abandon(self, pass_id: str) -> dict:
        """Abandons an active or paused pass for good: its open run is abandoned, nothing else changes."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            self._settle(conn)
            p = self._paused_or_active(conn, pass_id, "abandoned", ("active", "paused"))
            run = self._open_run(conn, p["id"])
            if run:
                conn.execute("UPDATE forecast_runs SET state = 'abandoned', closed_at = ? WHERE state = 'open' AND pass_id = ?",
                             (_now(), p["id"]))
                self._event(conn, p, "run_abandoned", "forecast", detail={"couple": run["couple"], "by": "pass_abandoned"})
            self._set_state(conn, p, "abandoned", "manual")
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
            self._event(conn, p, "run_abandoned", "forecast", detail={"couple": run["couple"], "by": "admin"})
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

        ponytail: stopgap while no script implements calc_orgunit_alerts (501); CSB alerts are then not computed.
        Remove this, the route and the etlui Skip button once the script exists (etlhub/docs/testing-QA/test-incident-log.md).
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

    # --- reading and unlocking ------------------------------------------------------------

    def progress(self, pass_id: str | None = None) -> dict:
        """State of a pass in the current mode (test or production): by default the active one, else the last one of
        the target month (`pass` null when that month has none yet: the first launch starts it)."""
        with self._transaction() as conn:
            self._settle(conn)
            p = self._get_pass(conn, pass_id) if pass_id else self._shown(conn)
            rows = self._rows(conn, p["id"]) if p else {}
            run = self._open_run(conn, p["id"]) if p else None
            cycle = p["cycle"] if p else self._target(conn)
            lock = conn.execute("SELECT job_id, task, acquired_at FROM pipeline_lock").fetchone()
        state = progress(rows, run["couple"] if run else None)
        state["cycle"] = cycle
        state["pass"] = p
        state["run"] = run
        state["lock"] = dict(zip(("job_id", "task", "acquired_at"), lock)) if lock else None
        state["test_mode"] = self._test_mode()
        state["dry_run"] = self._dry_run()  # read only, from .env: whether the scripts write to DHIS2
        return state

    # --- test mode (TEST_MODE) ---------------------------------------------------------------

    def set_mode(self, test_mode: bool) -> dict:
        """Switches TEST_MODE (where the pipeline state lives; DRYRUN, .env, stays as it is). Refused while a job runs.

        Leaving test mode pauses the active test pass: all test state stays in Redis, to resume in test mode.
        """
        current = self._test_mode()
        if test_mode == current:
            return {"test_mode": current}
        if current:  # test -> production
            with self._memory_transaction() as conn:
                self._check_lock_free(conn)
                if active := self._active(conn):
                    self._set_state(conn, active, "paused", "test_exit")
        with self._file_transaction() as conn:
            if not current:
                self._check_lock_free(conn)
            # A production fact (production paused or resumed): in the active production pass, if any.
            self._event(conn, self._pass_of(conn, None), "mode_changed", detail={"to": "test" if test_mode else "production"})
            self._set_test_mode(test_mode)
        return {"test_mode": test_mode}

    def release_lock(self) -> str | None:
        """Manual unlock (killed worker): its running checkpoint becomes error. Returns the freed job_id."""
        with self._transaction() as conn:
            row = conn.execute("SELECT job_id, task FROM pipeline_lock").fetchone()
            if row:
                conn.execute("UPDATE checkpoints SET status = 'error', updated_at = ?"
                             " WHERE job_id = ? AND status = 'running'", (_now(), row[0]))
                conn.execute("DELETE FROM pipeline_lock WHERE job_id = ?", (row[0],))
                step, item, pass_id = self._launched(conn, row[0]) or (None, None, None)
                self._event(conn, self._pass_of(conn, pass_id), "lock_released", step, item, row[0], {"task": row[1]})
        return row[0] if row else None

    # --- journal ------------------------------------------------------------------------------

    def journal(self, pass_id: str) -> list[dict]:
        """Events of a pass, oldest first. A pass lives in one store: production (SQLite file) or test (Redis blob)."""
        events = []
        for mode, store in (("production", self._file_transaction), ("test", self._test_journal)):
            with store() as conn:
                events += self._events(conn, pass_id, mode) if conn else []
        return events

    def cycles(self) -> list[dict]:
        """Every month with passes (and the target month), newest first; each with its passes, newest first.

        A pass: id, cycle, state, started_at, started_by, mode, events and last_at (mode_changed left out of both:
        they measure the pipeline's work, not the mode switches).
        """
        count = ("SELECT pass_id, count(*), max(at) FROM pipeline_events WHERE event != 'mode_changed'"
                 " AND pass_id IS NOT NULL GROUP BY pass_id")
        passes = []
        for mode, store in (("production", self._file_transaction), ("test", self._test_journal)):
            with store() as conn:
                stats = {p: (n, at) for p, n, at in conn.execute(count)} if conn else {}
                passes += [{**p, "mode": mode, **dict(zip(("events", "last_at"), stats.get(p["id"], (0, None))))}
                           for p in (self._passes(conn) if conn else [])]
        with self._transaction() as conn:
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


def get_checkpoint_store() -> CheckpointStore:
    global _checkpoint_store
    if _checkpoint_store is None:
        with _lock:
            if _checkpoint_store is None:
                _checkpoint_store = CheckpointStore()
    return _checkpoint_store
