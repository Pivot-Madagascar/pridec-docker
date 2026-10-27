from functools import lru_cache

import redis

from etlhub.core.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    """One shared client (and connection pool) per process."""
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
