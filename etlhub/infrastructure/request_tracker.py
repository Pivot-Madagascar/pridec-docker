import json
import logging
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from etlhub.core.config import get_settings

logger = logging.getLogger(__name__)

_request_tracker = None
_lock = threading.Lock()

# Older entries are deleted on each save (indexed on created_at, so cheap), except those a production pipeline
# journal event refers to (`journal` flag): a cycle's journal keeps its requests.
RETENTION_DAYS = 30

_SCHEMA = """
CREATE TABLE IF NOT EXISTS request_log (
    request_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
    url TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_request_log_created_at ON request_log(created_at);
"""


class RequestTracker:
    """HTTP request log, in SQLite only (`logs/etlhub.db`)."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path or Path(get_settings().logs_dir) / "etlhub.db")

    def _connect(self) -> sqlite3.Connection:
        # One short connection per call: safe across threads and Celery forks.
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        return conn

    def save(self, log: dict) -> None:
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT OR REPLACE INTO request_log (request_id, url, data) VALUES (?, ?, ?)",
                    (log["request_id"], log.get("url", ""), json.dumps(log)),
                )
                conn.execute(
                    "DELETE FROM request_log WHERE created_at < strftime('%Y-%m-%dT%H:%M:%f', 'now', ?)"
                    " AND json_extract(data, '$.journal') IS NULL",
                    (f"-{RETENTION_DAYS} days",),
                )
        except sqlite3.Error:
            logger.warning("Could not store request log %s", log.get("request_id"), exc_info=True)

    def get(self, request_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT data FROM request_log WHERE request_id = ?", (request_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def get_many(self, request_ids: set[str]) -> dict[str, dict]:
        """The logs of these requests that still exist, by request_id."""
        ids = list(request_ids)  # an empty IN () is valid SQLite
        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"SELECT request_id, data FROM request_log WHERE request_id IN ({', '.join('?' * len(ids))})", ids
            ).fetchall()
        return {request_id: json.loads(data) for request_id, data in rows}

    def list_recent(self, limit: int = 50, endpoint: str | None = None) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT data FROM request_log"
                " WHERE :endpoint IS NULL OR instr(url, :endpoint) > 0"
                " ORDER BY created_at DESC, rowid DESC LIMIT :limit",
                {"endpoint": endpoint, "limit": limit},
            ).fetchall()
        return [json.loads(r[0]) for r in rows]


def get_request_tracker() -> RequestTracker:
    global _request_tracker
    if _request_tracker is None:
        with _lock:
            if _request_tracker is None:
                _request_tracker = RequestTracker()
    return _request_tracker
