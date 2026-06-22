import json
import io
from pathlib import Path
import sys
import contextlib
import redis
from etlhub.core.config import get_settings


class JobStore:
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

    def get(self, job_id: str) -> dict | None:
        try:
            redis_client = self._get_redis()
            data = redis_client.get(f"job:{job_id}")
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def set(self, job_id: str, data: dict) -> None:
        try:
            redis_client = self._get_redis()
            redis_client.setex(
                f"job:{job_id}",
                86400,
                json.dumps(data)
            )
        except Exception:
            pass

    def save_logs(self, job_id: str, logs: str) -> None:
        try:
            redis_client = self._get_redis()
            redis_client.setex(
                f"etl_logs:{job_id}",
                86400,
                logs,
            )
        except Exception:
            pass
        try:
            settings = get_settings()
            logs_dir = Path(settings.logs_dir)
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / f"{job_id}.log").write_text(logs)
        except Exception:
            pass

    def get_logs(self, job_id: str) -> str | None:
        try:
            redis_client = self._get_redis()
            data = redis_client.get(f"etl_logs:{job_id}")
            if data:
                return data
        except Exception:
            pass
        log_file = Path(get_settings().logs_dir) / f"{job_id}.log"
        if log_file.exists():
            return log_file.read_text()
        return None

    def load_from_file(self, job_id: str, logs_dir: str) -> dict | None:
        status_file = Path(logs_dir) / f"{job_id}.json"
        if status_file.exists():
            return json.loads(status_file.read_text())
        return None