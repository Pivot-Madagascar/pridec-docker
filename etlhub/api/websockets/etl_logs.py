import asyncio
import json
import logging
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
            f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
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


async def handle_etl_logs_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()

    try:
        history = await _get_history(job_id)
        if history is None:
            await websocket.close(code=4004, reason="No job history found")
            return

        await websocket.send_json({
            "type": "etl_log_history",
            "job_id": job_id,
            "logs": history,
        })

        status = await _get_status(job_id)
        
        if status and status.get("status") in ("success", "error"):
            await websocket.send_json({
                "type": "job_status_update",
                "job_id": job_id,
                "status": status.get("status"),
                "message": status.get("message"),
                "timestamp": status.get("started"),
            })
            await websocket.send_json({
                "type": "etl_log_complete",
                "job_id": job_id,
                "final_status": status.get("status"),
            })
            await websocket.close(code=1000)
            return

        if status:
            await websocket.send_json({
                "type": "job_status_update",
                "job_id": job_id,
                "status": status.get("status", "unknown"),
                "message": status.get("message"),
                "timestamp": status.get("started"),
            })

        await _listen_for_updates(websocket, job_id)

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from job {job_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011, reason="Internal error")


async def _listen_for_updates(websocket: WebSocket, job_id: str):
    client = await get_redis_client()
    pubsub = client.pubsub()
    
    try:
        await pubsub.subscribe(f"etl_logs:{job_id}", f"etl_status:{job_id}")
        
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=30.0
                )
                
                if message:
                    try:
                        data = json.loads(message["data"])
                        await websocket.send_json(data)
                        
                        if data.get("type") == "job_status_update" and \
                           data.get("status") in ("success", "error"):
                            await websocket.send_json({
                                "type": "etl_log_complete",
                                "job_id": job_id,
                                "final_status": data.get("status"),
                            })
                            await websocket.close(code=1000)
                            return
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in Redis message: {e}")
                        
            except asyncio.TimeoutError:
                continue
                
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error(f"Error listening for updates: {e}")
    finally:
        await pubsub.unsubscribe(f"etl_logs:{job_id}", f"etl_status:{job_id}")
        await pubsub.close()