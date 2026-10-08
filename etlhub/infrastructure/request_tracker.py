import json
import logging
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from etlhub.core.config import get_settings
from etlhub.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

_request_tracker = None
_lock = threading.Lock()

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
    _redis_client = None

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path or Path(get_settings().logs_dir) / "etlhub.db")

    def _get_redis(self):
        if self._redis_client is None:
            self._redis_client = get_redis()
        return self._redis_client

    def _connect(self) -> sqlite3.Connection:
        # One short connection per call: safe across threads and Celery forks.
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        return conn

    def save(self, log: dict) -> None:
        try:
            redis_client = self._get_redis()
            redis_client.setex(
                f"req:{log['request_id']}",
                86400,
                json.dumps(log),
            )
        except Exception:
            pass
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT OR REPLACE INTO request_log (request_id, url, data) VALUES (?, ?, ?)",
                    (log["request_id"], log.get("url", ""), json.dumps(log)),
                )
        except sqlite3.Error:
            logger.warning("Could not store request log %s", log.get("request_id"), exc_info=True)

    def get(self, request_id: str) -> dict | None:
        try:
            redis_client = self._get_redis()
            data = redis_client.get(f"req:{request_id}")
            if data:
                return json.loads(data)
        except Exception:
            pass
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT data FROM request_log WHERE request_id = ?", (request_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

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
