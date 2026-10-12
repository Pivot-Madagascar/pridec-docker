import base64
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
from etlhub.domain import pipeline
from etlhub.domain.exceptions import ConfirmationRequiredError, ETLException, PipelineBlockedError
from etlhub.domain.pipeline import (
    accessible_steps, blocking_reason, config_item, cycle_for_launch, dependents, disease_of, impact, level_of,
    progress, require_confirmation, require_input_confirmation, resolve_slot, run_context, run_items, status,
)
from etlhub.infrastructure.config_store import ConfigStore
from etlhub.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

_checkpoint_store = None
_lock = threading.Lock()

# Same db as request_log, but no retention: a cycle must stay readable.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    cycle      TEXT NOT NULL,
    step       TEXT NOT NULL,
    item       TEXT NOT NULL,
    job_id     TEXT,
    status     TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (cycle, step, item)
);
CREATE INDEX IF NOT EXISTS ix_checkpoints_job_id ON checkpoints(job_id);
CREATE TABLE IF NOT EXISTS pipeline_lock (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    job_id      TEXT NOT NULL,
    task        TEXT NOT NULL,
    acquired_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS forecast_runs (
    cycle         TEXT NOT NULL,
    couple        TEXT NOT NULL,
    state         TEXT NOT NULL,
    disease_code  TEXT NOT NULL,
    ou_level      TEXT NOT NULL,
    alert_name    TEXT,
    external_data TEXT NOT NULL DEFAULT 'none',
    opened_at     TEXT NOT NULL,
    closed_at     TEXT,
    PRIMARY KEY (cycle, couple, opened_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_run ON forecast_runs(state) WHERE state = 'open';
"""
_RUN_COLUMNS = ("cycle", "couple", "state", "disease_code", "ou_level", "alert_name", "external_data", "opened_at")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def apply_to_config_store(context: dict[str, str | None]) -> None:
    """Writes the run context where the ETL scripts read it (etl/scripts/config.py reads Redis first)."""
    store = ConfigStore()
    written = store.set_all({k: v for k, v in context.items() if v is not None})
    cleared = store.delete_keys([k for k, v in context.items() if v is None])
    if not (written and cleared):
        raise ETLException("Could not write the forecast run context (DISEASE_CODE, OU_LEVEL) to Redis")


def dry_run_enabled() -> bool:
    """Same source as the ETL scripts: DRYRUN in the dynamic config (Redis), else .env, default true."""
    from etl.scripts.config import get_dry_run
    return get_dry_run()


def write_dry_run(value: bool) -> None:
    if not ConfigStore().set_all({"DRYRUN": "true" if value else "false"}):
        raise ETLException("Could not write DRYRUN to Redis")


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
                 dry_run: Callable[[], bool] = dry_run_enabled, set_dry_run: Callable[[bool], None] = write_dry_run,
                 blob: RedisBlob | None = None):
        """In test mode (DRYRUN=true) everything is kept in Redis (`blob`), never in the SQLite file."""
        settings = get_settings()
        self._dry_run, self._set_dry_run = dry_run, set_dry_run
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
        return self._uploads_root / "dry_run" if self._dry_run() else self._uploads_root

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Same SQL in both modes: the SQLite file in production, an in-memory copy kept in Redis in test mode."""
        transaction = self._memory_transaction if self._dry_run() else self._file_transaction
        with transaction() as conn:
            yield conn

    @contextmanager
    def _memory_transaction(self) -> Iterator[sqlite3.Connection]:
        with self._blob.lock(), closing(sqlite3.connect(":memory:", isolation_level=None)) as conn:
            data = self._blob.get()
            if data:
                conn.deserialize(data)
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
            conn.executescript(_SCHEMA)
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    @staticmethod
    def _rows(conn: sqlite3.Connection, cycle: str) -> pipeline.Rows:
        rows = conn.execute(
            "SELECT step, item, status, job_id, updated_at FROM checkpoints WHERE cycle = ?", (cycle,)
        ).fetchall()
        return {(s, i): {"status": st, "job_id": j, "updated_at": u} for s, i, st, j, u in rows}

    def _active(self, conn: sqlite3.Connection) -> tuple[str | None, bool]:
        """The latest cycle (YYYYMM sorts chronologically) and whether it is complete."""
        active = conn.execute(
            "SELECT max(cycle) FROM (SELECT cycle FROM checkpoints UNION SELECT cycle FROM forecast_runs)"
        ).fetchone()[0]
        complete = active is not None and progress(self._rows(conn, active))["current_step"] is None
        return active, complete

    def _launch_cycle(self, conn: sqlite3.Connection) -> str:
        """The calendar month. A run still open from a previous month is abandoned (automatic switch)."""
        cycle = cycle_for_launch(*self._active(conn), pipeline.this_month())
        conn.execute("UPDATE forecast_runs SET state = 'abandoned', closed_at = ? WHERE state = 'open' AND cycle != ?",
                     (_now(), cycle))
        return cycle

    @staticmethod
    def _open_run(conn: sqlite3.Connection) -> dict | None:
        row = conn.execute(f"SELECT {', '.join(_RUN_COLUMNS)} FROM forecast_runs WHERE state = 'open'").fetchone()
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
    def _upsert(conn: sqlite3.Connection, cycle: str, step: str, item: str, job_id: str | None, state: str) -> None:
        conn.execute(
            "INSERT INTO checkpoints (cycle, step, item, job_id, status, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (cycle, step, item) DO UPDATE SET"
            " job_id = excluded.job_id, status = excluded.status, updated_at = excluded.updated_at",
            (cycle, step, item, job_id, state, _now()),
        )

    @staticmethod
    def _reset(conn: sqlite3.Connection, cycle: str, items: list[str]) -> None:
        """Back to pending = no row (forecast step only)."""
        conn.executemany("DELETE FROM checkpoints WHERE cycle = ? AND step = 'forecast' AND item = ?",
                         [(cycle, i) for i in items])

    def _kept_file(self, cycle: str, name: str, couple: str) -> Path:
        """config.json is kept per disease, external_data.csv per org unit level (fkt or csb)."""
        key = f"config_{disease_of(couple)}.json" if name == "config" else f"external_data_{level_of(couple)}.csv"
        return self._uploads_dir / cycle / key

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
        """
        with self._transaction() as conn:
            self._check_lock_free(conn)
            cycle = self._launch_cycle(conn)
            rows = self._rows(conn, cycle)
            run = self._open_run(conn)
            couple = run["couple"] if run else None
            step, item = resolve_slot(task, rows, couple)
            require_confirmation(step, item, rows, confirm)
            if step == "forecast":
                self._reset(conn, cycle, dependents(item))
            self._take_lock(conn, job_id, task)
            self._upsert(conn, cycle, step, item, job_id, "running")
            if step == "forecast":
                self._apply_context(run_context(couple))  # inside the transaction: a failure writes nothing

    def finish(self, job_id: str, state: str) -> None:
        """Records the final status (success | error) and frees the lock. A post_forecast success closes the run."""
        with self._transaction() as conn:
            row = conn.execute("SELECT step, item FROM checkpoints WHERE job_id = ?", (job_id,)).fetchone()
            conn.execute("UPDATE checkpoints SET status = ?, updated_at = ? WHERE job_id = ?", (state, _now(), job_id))
            conn.execute("DELETE FROM pipeline_lock WHERE job_id = ?", (job_id,))
            if row and state == "success" and row[0] == "forecast" and row[1].endswith(":post_forecast"):
                conn.execute("UPDATE forecast_runs SET state = 'closed', closed_at = ? WHERE state = 'open' AND couple = ?",
                             (_now(), row[1].split(":")[0]))

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

    def _check_input_change(self, conn: sqlite3.Connection, cycle: str, name: str, confirm: bool,
                            removed: bool) -> tuple[str, list[str]]:
        """Checks an upload or delete of config / external_data. Returns (couple, items to reset after it)."""
        rows = self._rows(conn, cycle)
        run = self._open_run(conn)
        if run is None:
            raise PipelineBlockedError(f"Changing {name} needs an open forecast run (POST /pipeline/runs)")
        couple = run["couple"]
        if name == "config" and not removed:
            reason = blocking_reason(rows, "forecast", config_item(couple), couple)
            if reason:
                raise PipelineBlockedError(reason)
        return couple, require_input_confirmation(name, couple, rows, confirm)

    @contextmanager
    def change_input(self, name: str, confirm: bool = False, removed: bool = False) -> Iterator[None]:
        """Upload (or delete, removed=True) of config.json / external_data.csv in the open run, under the lock.

        config is the item config/<disease>, shared by the disease's 3 runs; external_data is optional, one file
        per org unit level, recorded on the run. The file written in input/ is also kept in uploads/<cycle>/ and
        copied back when another run of the same disease (config) or level (external_data) opens.
        A change resets the open run from validate_inputs on, and needs confirm once that file was used.
        """
        action = "delete" if removed else "upload"
        job_id = f"{action}_{name}_{uuid.uuid4().hex[:8]}"
        with self._transaction() as conn:
            self._check_lock_free(conn)
            cycle = self._launch_cycle(conn)
            couple, reset = self._check_input_change(conn, cycle, name, confirm, removed)
            self._take_lock(conn, job_id, f"{action} {name}")
            if name == "config" and not removed:
                self._upsert(conn, cycle, "forecast", config_item(couple), job_id, "running")
        try:
            yield
            with self._transaction() as conn:
                self._reset(conn, cycle, reset)
                if name == "config":
                    if removed:
                        self._reset(conn, cycle, [config_item(couple)])
                    else:
                        self._upsert(conn, cycle, "forecast", config_item(couple), job_id, "success")
                else:
                    conn.execute("UPDATE forecast_runs SET external_data = ? WHERE state = 'open'",
                                 ("none" if removed else "uploaded",))
                self._keep(cycle, name, couple, removed)
                conn.execute("DELETE FROM pipeline_lock WHERE job_id = ?", (job_id,))
        except BaseException:  # the change itself or its recording: the lock must not stay taken
            self.finish(job_id, "error")
            raise

    def _keep(self, cycle: str, name: str, couple: str, removed: bool) -> None:
        kept = self._kept_file(cycle, name, couple)
        if removed:
            kept.unlink(missing_ok=True)
            return
        kept.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._input_dir / ("config.json" if name == "config" else "external_data.csv"), kept)

    def launch_cycle(self) -> str:
        """The cycle a launch would belong to now. PipelineBlockedError when the month already ran."""
        with self._transaction() as conn:
            return self._launch_cycle(conn)

    # --- forecast runs (R6) ---------------------------------------------------------------

    def open_run(self, couple: str, confirm: bool = False) -> dict:
        """Opens the forecast run of a couple: one at a time, step data_import done, input/ and output/ emptied.

        Reopening a couple already closed in the cycle needs confirm and resets all its items.
        """
        with self._transaction() as conn:
            self._check_lock_free(conn)
            cycle = self._launch_cycle(conn)
            rows = self._rows(conn, cycle)
            if "forecast" not in accessible_steps(rows):
                raise PipelineBlockedError("Opening a forecast run needs step data_import done first")
            current = self._open_run(conn)
            if current:
                raise PipelineBlockedError(f"Run {current['couple']} is open: finish or abandon it first")
            items = list(run_items(couple))
            closed = conn.execute("SELECT 1 FROM forecast_runs WHERE cycle = ? AND couple = ? AND state = 'closed'",
                                  (cycle, couple)).fetchone()
            if closed and not confirm:
                raise ConfirmationRequiredError(
                    f"Run {couple} is already closed in cycle {cycle}: resend with confirm=true to reopen it",
                    impact("forecast", couple, rows, items))
            self._reset(conn, cycle, items)
            context = run_context(couple)
            self._clear_workdirs()  # inside the transaction: if it fails, the run is not opened
            external = self._restore(cycle, couple, rows)
            run = {"cycle": cycle, "couple": couple, "state": "open", "disease_code": context["DISEASE_CODE"],
                   "ou_level": context["OU_LEVEL"], "alert_name": context["ALERT_NAME"], "external_data": external,
                   "opened_at": datetime.now().isoformat(timespec="microseconds")}
            conn.execute(f"INSERT INTO forecast_runs ({', '.join(_RUN_COLUMNS)})"
                         f" VALUES ({', '.join('?' * len(_RUN_COLUMNS))})", tuple(run[c] for c in _RUN_COLUMNS))
        return run

    def _restore(self, cycle: str, couple: str, rows: pipeline.Rows) -> str:
        """Copies the disease's config and the level's external_data, uploaded earlier in the cycle, into input/.

        Returns the run's external_data state (uploaded | none).
        """
        config = self._kept_file(cycle, "config", couple)
        external = self._kept_file(cycle, "external_data", couple)
        if config.is_file() and status(rows, "forecast", config_item(couple)) == "success":
            self._input_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(config, self._input_dir / "config.json")
        if not external.is_file():
            return "none"
        self._input_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(external, self._input_dir / "external_data.csv")
        return "uploaded"

    def abandon_run(self) -> str:
        """Abandons the open run: nothing is published, its items go back to pending. Returns the couple."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            run = self._open_run(conn)
            if run is None:
                raise PipelineBlockedError("No forecast run is open")
            conn.execute("UPDATE forecast_runs SET state = 'abandoned', closed_at = ? WHERE state = 'open'", (_now(),))
            self._reset(conn, run["cycle"], list(run_items(run["couple"])))
        return run["couple"]

    def decide(self, decision: str) -> str:
        """Approval of the open run's forecast: approve unlocks post_forecast, reject resets the forecast."""
        with self._transaction() as conn:
            self._check_lock_free(conn)
            cycle = self._launch_cycle(conn)
            rows = self._rows(conn, cycle)
            run = self._open_run(conn)
            if run is None:
                raise PipelineBlockedError("No forecast run is open")
            couple = run["couple"]
            if decision == "approve":
                reason = blocking_reason(rows, "forecast", f"{couple}:approve", couple)
                if reason:
                    raise PipelineBlockedError(reason)
                self._upsert(conn, cycle, "forecast", f"{couple}:approve", None, "success")
            else:
                forecast = f"{couple}:forecast"
                if status(rows, "forecast", forecast) != "success":
                    raise PipelineBlockedError(f"Nothing to reject: {forecast} is not in success")
                self._reset(conn, cycle, [forecast, *dependents(forecast)])
        return couple

    # --- reading and unlocking ------------------------------------------------------------

    def progress(self, cycle: str | None = None) -> dict:
        """State of a cycle, the current month by default, in the current mode (test or production)."""
        with self._transaction() as conn:
            cycle = cycle or pipeline.this_month()
            rows = self._rows(conn, cycle)
            run = self._open_run(conn)
            run = run if run and run["cycle"] == cycle else None
            lock = conn.execute("SELECT job_id, task, acquired_at FROM pipeline_lock").fetchone()
        state = progress(rows, run["couple"] if run else None)
        state["cycle"] = cycle
        state["cycle_state"] = "closed" if state["current_step"] is None else "open"
        state["run"] = run
        state["lock"] = dict(zip(("job_id", "task", "acquired_at"), lock)) if lock else None
        state["dry_run"] = self._dry_run()
        return state

    # --- test mode (DRYRUN) -----------------------------------------------------------------

    def set_mode(self, dry_run: bool, confirm: bool = False) -> dict:
        """Switches DRYRUN (read by the ETL scripts). Refused while a job runs.

        Leaving test mode discards the test checkpoints kept in Redis: confirm=true is needed when there are any.
        """
        current = self._dry_run()
        if dry_run == current:
            return {"dry_run": current}
        if not current:  # production -> test
            with self._transaction() as conn:
                self._check_lock_free(conn)
                self._set_dry_run(True)
            return {"dry_run": True}
        with self._blob.lock(), closing(sqlite3.connect(":memory:")) as conn:  # test -> production
            data = self._blob.get()
            if data:
                conn.deserialize(data)
                self._check_lock_free(conn)
                done = conn.execute("SELECT cycle, count(*) FROM checkpoints WHERE status = 'success' GROUP BY cycle").fetchall()
                run = self._open_run(conn)
                if not confirm:
                    raise ConfirmationRequiredError(
                        "Leaving test mode discards the test cycle and its open run: resend with confirm=true",
                        {"mode": "dry_run", "items_in_success": dict(done), "open_run": run["couple"] if run else None})
            self._blob.delete()
            shutil.rmtree(self._uploads_root / "dry_run", ignore_errors=True)
            self._set_dry_run(False)
        return {"dry_run": False}

    def release_lock(self) -> str | None:
        """Manual unlock (killed worker): its running checkpoint becomes error. Returns the freed job_id."""
        with self._transaction() as conn:
            row = conn.execute("SELECT job_id FROM pipeline_lock").fetchone()
            if row:
                conn.execute("UPDATE checkpoints SET status = 'error', updated_at = ?"
                             " WHERE job_id = ? AND status = 'running'", (_now(), row[0]))
                conn.execute("DELETE FROM pipeline_lock WHERE job_id = ?", (row[0],))
        return row[0] if row else None


def get_checkpoint_store() -> CheckpointStore:
    global _checkpoint_store
    if _checkpoint_store is None:
        with _lock:
            if _checkpoint_store is None:
                _checkpoint_store = CheckpointStore()
    return _checkpoint_store
