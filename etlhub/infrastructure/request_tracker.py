import json
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import time
import threading

import redis
from etlhub.core.config import get_settings

_request_tracker = None
_lock = threading.Lock()


class RequestTracker:
    _redis_client = None

    def _get_redis(self):
        if self._redis_client is None:
            settings = get_settings()
            self._redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
            )
        return self._redis_client

    def _logs_path(self):
        settings = get_settings()
        return Path(settings.logs_dir) / "requests"

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
            path = self._logs_path() / f"{log['request_id']}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(log, indent=2))
        except Exception:
            pass

    def get(self, request_id: str) -> dict | None:
        try:
            redis_client = self._get_redis()
            data = redis_client.get(f"req:{request_id}")
            if data:
                return json.loads(data)
        except Exception:
            pass
        path = self._logs_path() / f"{request_id}.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return None

    def list_recent(self, limit: int = 50) -> list[dict]:
        try:
            path = self._logs_path()
            if not path.exists():
                return []
            files = sorted(path.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            results = []
            for f in files[:limit]:
                try:
                    results.append(json.loads(f.read_text()))
                except Exception:
                    continue
            return results
        except Exception:
            return []


def get_request_tracker() -> RequestTracker:
    global _request_tracker
    if _request_tracker is None:
        with _lock:
            if _request_tracker is None:
                _request_tracker = RequestTracker()
    return _request_tracker
