import json
from datetime import datetime, timezone

from etlhub.infrastructure.redis_client import get_redis


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_log(job_id: str, level: str, message: str) -> None:
    get_redis().publish(f"etl_logs:{job_id}", json.dumps({
        "type": "etl_log_entry",
        "job_id": job_id,
        "timestamp": _now(),
        "level": level,
        "message": message,
        "source": "etl-processor",
    }))


def publish_status(job_id: str, status: str, message: str | None = None) -> None:
    get_redis().publish(f"etl_status:{job_id}", json.dumps({
        "type": "job_status_update",
        "job_id": job_id,
        "status": status,
        "message": message,
        "timestamp": _now(),
    }))
