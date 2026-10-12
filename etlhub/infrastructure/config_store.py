import redis
import logging
from etlhub.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

CONFIG_KEY = "app:config:dynamic"

class ConfigStore:
    def get_all(self) -> dict:
        try:
            return get_redis().hgetall(CONFIG_KEY) or {}
        except redis.RedisError as e:
            logger.warning(f"ConfigStore: Redis unavailable, using .env fallback: {e}")
            return {}

    def set_all(self, config: dict) -> bool:
        str_config = {k: str(v) for k, v in config.items() if v is not None}
        try:
            get_redis().hset(CONFIG_KEY, mapping=str_config)
            return True
        except redis.RedisError as e:
            logger.error(f"ConfigStore: failed to write to Redis: {e}")
            return False

    def delete_keys(self, keys: list) -> bool:
        try:
            if keys:
                get_redis().hdel(CONFIG_KEY, *keys)
            return True
        except redis.RedisError as e:
            logger.error(f"ConfigStore: failed to delete keys from Redis: {e}")
            return False