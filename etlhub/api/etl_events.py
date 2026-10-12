import json
from functools import lru_cache
from datetime import datetime, timezone

from etlhub.infrastructure.redis_client import get_redis


class ETLEventManager:
    def publish_log(self, job_id: str, level: str, message: str, source: str = "etl-processor"):
        client = get_redis()
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
        client = get_redis()
        payload = json.dumps({
            "type": "job_status_update",
            "job_id": job_id,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        })
        client.publish(f"etl_status:{job_id}", payload)


@lru_cache
def get_etl_event_manager() -> ETLEventManager:
    return ETLEventManager()
