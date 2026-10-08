import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import redis.asyncio as aioredis
from etlhub.core.config import get_settings

logger = logging.getLogger(__name__)

redis_pool: Optional[aioredis.ConnectionPool] = None

async def get_redis_client() -> aioredis.Redis:
    global redis_pool
    if redis_pool is None:
        settings = get_settings()
        redis_pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=10,
        )
    return aioredis.Redis(connection_pool=redis_pool)


async def _get_history(job_id: str) -> Optional[str]:
    settings = get_settings()
    log_file = Path(settings.logs_dir) / f"{job_id}.log"

    try:
        client = await get_redis_client()
        data = await client.get(f"etl_logs:{job_id}")
        if data:
            return data
    except aioredis.RedisError as e:
        logger.warning(f"Redis error fetching history: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching history: {e}")

    if log_file.exists():
        try:
            return log_file.read_text()
        except IOError as e:
            logger.error(f"Error reading log file: {e}")
    
    return None


async def _get_status(job_id: str) -> Optional[dict]:
    try:
        client = await get_redis_client()
        data = await client.get(f"job:{job_id}")
        if data:
            return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in job status: {e}")
    except aioredis.RedisError as e:
        logger.warning(f"Redis error fetching status: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching status: {e}")
    
    return None


FINAL_STATUSES = ("success", "error")
POLL_SECONDS = 1.0           # wait for a pub/sub message at most this long per loop turn
STATUS_CHECK_SECONDS = 10.0  # re-read job:{id} this often, in case the final event was missed


async def _send_status(websocket: WebSocket, job_id: str, status: dict) -> None:
    await websocket.send_json({
        "type": "job_status_update",
        "job_id": job_id,
        "status": status.get("status", "unknown"),
        "message": status.get("message"),
        "timestamp": status.get("started"),
    })


async def _complete(websocket: WebSocket, job_id: str, final_status: str | None) -> None:
    await websocket.send_json({"type": "etl_log_complete", "job_id": job_id, "final_status": final_status})
    await websocket.close(code=1000)


async def handle_etl_logs_ws(websocket: WebSocket, job_id: str):
    """Stream a job's logs: history first, then live entries until the job ends.

    Closes with 4004 only for an unknown job (no job record and no logs). A known job
    that has not logged anything yet gets an empty history and stays connected.
    """
    # The session and origin are checked by the router dependency (get_current_user).
    await websocket.accept()
    client = await get_redis_client()
    pubsub = client.pubsub()
    # Notices the browser closing the socket while we wait for Redis.
    client_gone = asyncio.create_task(websocket.receive())

    try:
        # Subscribe before reading history and status: nothing published in between is lost.
        await pubsub.subscribe(f"etl_logs:{job_id}", f"etl_status:{job_id}")
        history = await _get_history(job_id)
        status = await _get_status(job_id)

        if history is None and status is None:
            await websocket.close(code=4004, reason="Unknown job")
            return

        await websocket.send_json({"type": "etl_log_history", "job_id": job_id, "logs": history or ""})

        if status is None:
            # Logs without a job record: the record expired (24 h), the job is long over.
            await _complete(websocket, job_id, None)
            return
        await _send_status(websocket, job_id, status)
        if status.get("status") in FINAL_STATUSES:
            await _complete(websocket, job_id, status["status"])
            return

        await _listen_for_updates(websocket, pubsub, job_id, client_gone)

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from job {job_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011, reason="Internal error")
    finally:
        client_gone.cancel()
        try:
            await pubsub.unsubscribe()
            await pubsub.aclose()
        except Exception as e:
            logger.warning(f"Error closing pub/sub for job {job_id}: {e}")


async def _listen_for_updates(websocket: WebSocket, pubsub, job_id: str, client_gone: asyncio.Task):
    last_check = time.monotonic()
    while not client_gone.done():
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=POLL_SECONDS)
        if message:
            try:
                data = json.loads(message["data"])
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid JSON in Redis message: {e}")
                continue
            await websocket.send_json(data)
            if data.get("type") == "job_status_update" and data.get("status") in FINAL_STATUSES:
                await _complete(websocket, job_id, data["status"])
                return
        elif time.monotonic() - last_check >= STATUS_CHECK_SECONDS:
            last_check = time.monotonic()
            status = await _get_status(job_id)
            if status and status.get("status") in FINAL_STATUSES:
                await _send_status(websocket, job_id, status)
                await _complete(websocket, job_id, status["status"])
                return
    logger.info(f"Client disconnected from job {job_id}")
