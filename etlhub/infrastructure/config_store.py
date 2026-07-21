import redis
import logging
from etlhub.core.config import get_settings

logger = logging.getLogger(__name__)

CONFIG_KEY = "app:config:dynamic"

class ConfigStore:
    def __init__(self):
        self._client = None

    def _get_client(self) -> redis.Redis:
        if self._client is None:
            s = get_settings()
            self._client = redis.Redis(
                host=s.redis_host, port=s.redis_port, db=s.redis_db,
                decode_responses=True,
            )
        return self._client

    def get_all(self) -> dict:
        try:
            return self._get_client().hgetall(CONFIG_KEY) or {}
        except redis.RedisError as e:
            logger.warning(f"ConfigStore: Redis unavailable, using .env fallback: {e}")
            return {}

    def set_all(self, config: dict) -> bool:
        str_config = {k: str(v) for k, v in config.items() if v is not None}
        try:
            self._get_client().hset(CONFIG_KEY, mapping=str_config)
            return True
        except redis.RedisError as e:
            logger.error(f"ConfigStore: failed to write to Redis: {e}")
            return False

    def delete_keys(self, keys: list) -> bool:
        try:
            if keys:
                self._get_client().hdel(CONFIG_KEY, *keys)
            return True
        except redis.RedisError as e:
            logger.error(f"ConfigStore: failed to delete keys from Redis: {e}")
            return False