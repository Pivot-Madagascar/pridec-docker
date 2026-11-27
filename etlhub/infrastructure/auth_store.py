"""DHIS2 login state kept in Redis.

- `dhis2:credential:{username}`: the DHIS2 personal access token of each account (one per account, 30 days). The ETL
  scripts read the most recently created one (`get_credential()` without a username).
- `session:{sha256(id)}`: browser sessions; only the hash of the session id is stored.
- `login:fail:{ip}:{username}`: failed login counter.

A credential is written with its token's lifetime (EX), so Redis deletes it when DHIS2 stops accepting the token;
a session lives 24 h. Redis persistence (AOF) keeps them
across restarts; there is no other copy.

A Redis failure raises the domain's AuthStoreUnavailable (get_credential returns None instead).
"""
import functools
import hashlib
import json
import logging
import secrets

import redis

from etlhub.domain.exceptions import AuthStoreUnavailable
from etlhub.infrastructure.redis_client import get_redis

logger = logging.getLogger(__name__)

CREDENTIAL_KEY = "dhis2:credential"  # prefix of the per-account keys


def _unavailable(function):
    """Redis errors become the domain's AuthStoreUnavailable (same message): callers never see redis."""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except redis.RedisError as e:
            raise AuthStoreUnavailable(str(e)) from e
    return wrapper


def _credential_key(username: str) -> str:
    return f"{CREDENTIAL_KEY}:{username.lower()}"


def _session_key(session_id: str) -> str:
    return "session:" + hashlib.sha256(session_id.encode()).hexdigest()


def get_credential(username: str | None = None) -> dict | None:
    """{url, token, pat_uid, username, expires_at, device} of `username`'s token; without a username, the most recently
    created token of all accounts (the ETL jobs'). None when missing, expired or Redis is down."""
    try:
        r = get_redis()
        if username:
            data = r.get(_credential_key(username))
            return json.loads(data) if data else None
        credentials = [json.loads(d) for d in (r.get(k) for k in r.scan_iter(f"{CREDENTIAL_KEY}:*")) if d]
    except redis.RedisError as e:
        logger.warning("Cannot read the DHIS2 credential from Redis: %s", e)
        return None
    return max(credentials, key=lambda c: c.get("created_at", c["expires_at"]), default=None)


@_unavailable
def set_credential(credential: dict, ttl: int) -> None:
    get_redis().set(_credential_key(credential["username"]), json.dumps(credential), ex=ttl)


@_unavailable
def delete_credential(username: str) -> None:
    get_redis().delete(_credential_key(username))


@_unavailable
def create_session(user: dict, pat_uid: str, ttl: int) -> str:
    """A new session starts in test mode: the user chooses production on Home."""
    session_id = secrets.token_urlsafe(32)
    get_redis().set(_session_key(session_id), json.dumps({"user": user, "pat_uid": pat_uid, "test_mode": True}), ex=ttl)
    return session_id


@_unavailable
def set_session_mode(session_id: str, test_mode: bool) -> bool:
    """The user's mode, in their session only (never the server's): False when the session is gone."""
    key = _session_key(session_id)
    data, ttl = get_redis().get(key), get_redis().ttl(key)
    if not data or ttl <= 0:
        return False
    get_redis().set(key, json.dumps({**json.loads(data), "test_mode": test_mode}), ex=ttl)
    return True


@_unavailable
def get_session(session_id: str) -> dict | None:
    data = get_redis().get(_session_key(session_id))
    return json.loads(data) if data else None


@_unavailable
def delete_session(session_id: str) -> None:
    get_redis().delete(_session_key(session_id))


def _fail_key(ip: str, username: str) -> str:
    return f"login:fail:{ip}:{username.lower()}"


@_unavailable
def failed_logins(ip: str, username: str) -> int:
    return int(get_redis().get(_fail_key(ip, username)) or 0)


@_unavailable
def record_failed_login(ip: str, username: str, window: int) -> None:
    key = _fail_key(ip, username)
    pipe = get_redis().pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()


@_unavailable
def clear_failed_logins(ip: str, username: str) -> None:
    get_redis().delete(_fail_key(ip, username))
