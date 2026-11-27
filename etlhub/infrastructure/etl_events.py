import json
from datetime import datetime, timezone

import redis.asyncio as aioredis

from etlhub.core.config import get_settings
from etlhub.infrastructure.redis_client import get_redis

_async_pool: aioredis.ConnectionPool | None = None


def _async_redis() -> aioredis.Redis:
    """The log WebSockets' client: one async pool per process (the event loop's), opened at the first subscription."""
    global _async_pool
    if _async_pool is None:
        _async_pool = aioredis.ConnectionPool.from_url(get_settings().redis_url, decode_responses=True, max_connections=10)
    return aioredis.Redis(connection_pool=_async_pool)


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


class RedisEventSubscriber:
    """EventSubscriber on the channels publish_log and publish_status write to. One per WebSocket."""

    def __init__(self) -> None:
        self._pubsub = None  # opened by subscribe

    async def subscribe(self, job_id: str) -> None:
        self._pubsub = _async_redis().pubsub()
        await self._pubsub.subscribe(f"etl_logs:{job_id}", f"etl_status:{job_id}")

    async def next_event(self, timeout: float) -> str | None:
        message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
        return message["data"] if message else None

    async def close(self) -> None:
        if self._pubsub is not None:
            await self._pubsub.unsubscribe()
            await self._pubsub.aclose()
