import redis
import logging
from dotenv import dotenv_values
from etlhub.core.config import ENV_FILE
from etlhub.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

CONFIG_KEY = "app:config:dynamic"

# The runtime config of the ETL scripts under etlhub (etlhub/script_config.py reads them here, never from .env).
# .env holds their defaults: load_env() copies them at each API start and on "Reload from .env".
# Never a secret: Redis is persisted on disk (AOF).
EDITABLE_KEYS = ("PARENT_OU", "OU_LEVEL", "DISEASE_CODE", "DRYRUN", "LOG_LEVEL", "GEE_VARIABLES")

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

    def load_env(self) -> bool:
        """Overwrites EDITABLE_KEYS with the values of etlhub's env file (ENV_FILE, root .env by default).
        A key missing from it is removed: the scripts then use their default."""
        env = dotenv_values(ENV_FILE)
        present = {k: env[k] for k in EDITABLE_KEYS if env.get(k) is not None}
        # hset refuses an empty mapping
        return self.delete_keys([k for k in EDITABLE_KEYS if k not in present]) and (not present or self.set_all(present))
