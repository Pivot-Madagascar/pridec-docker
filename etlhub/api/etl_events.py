import json
from datetime import datetime, timezone

from etlhub.infrastructure.redis_client import get_redis


class ETLEventManager:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = get_redis()
        return self._client

    def publish_log(self, job_id: str, level: str, message: str, source: str = "etl-processor"):
        client = self._get_client()
        payload = json.dumps({
            "type": "etl_log_entry",
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": level,
            "message": message,
            "source": source,
        })
        client.publish(f"etl_logs:{job_id}", payload)

    def publish_status(self, job_id: str, status: str, message: str | None = None):
        client = self._get_client()
        payload = json.dumps({
            "type": "job_status_update",
            "job_id": job_id,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        })
        client.publish(f"etl_status:{job_id}", payload)


_event_manager = None


def get_etl_event_manager() -> ETLEventManager:
    global _event_manager
    if _event_manager is None:
        _event_manager = ETLEventManager()
    return _event_manager
