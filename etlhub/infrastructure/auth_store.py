"""DHIS2 login state kept in Redis.

- `dhis2:credential`: the one active DHIS2 personal access token, read by the ETL scripts.
- `session:{sha256(id)}`: browser sessions; only the hash of the session id is stored.
- `login:fail:{ip}:{username}`: failed login counter.

Credential and sessions are written with the token's remaining lifetime (EX), so Redis
deletes them when DHIS2 stops accepting the token. Redis persistence (AOF) keeps them
across restarts; there is no other copy.
"""
import hashlib
import json
import logging
import secrets

import redis

from etlhub.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

CREDENTIAL_KEY = "dhis2:credential"


def _session_key(session_id: str) -> str:
    return "session:" + hashlib.sha256(session_id.encode()).hexdigest()


def get_credential() -> dict | None:
    """Return {url, token, pat_uid, username, expires_at} or None (missing, expired, Redis down)."""
    try:
        data = get_redis().get(CREDENTIAL_KEY)
    except redis.RedisError as e:
        logger.warning("Cannot read the DHIS2 credential from Redis: %s", e)
        return None
    return json.loads(data) if data else None


def set_credential(credential: dict, ttl: int) -> None:
    get_redis().set(CREDENTIAL_KEY, json.dumps(credential), ex=ttl)


def delete_credential() -> None:
    get_redis().delete(CREDENTIAL_KEY)


def create_session(user: dict, pat_uid: str, ttl: int) -> str:
    session_id = secrets.token_urlsafe(32)
    get_redis().set(_session_key(session_id), json.dumps({"user": user, "pat_uid": pat_uid}), ex=ttl)
    return session_id


def get_session(session_id: str) -> dict | None:
    data = get_redis().get(_session_key(session_id))
    return json.loads(data) if data else None


def delete_session(session_id: str) -> None:
    get_redis().delete(_session_key(session_id))


def _fail_key(ip: str, username: str) -> str:
    return f"login:fail:{ip}:{username.lower()}"


def failed_logins(ip: str, username: str) -> int:
    return int(get_redis().get(_fail_key(ip, username)) or 0)


def record_failed_login(ip: str, username: str, window: int) -> None:
    key = _fail_key(ip, username)
    pipe = get_redis().pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()


def clear_failed_logins(ip: str, username: str) -> None:
    get_redis().delete(_fail_key(ip, username))
