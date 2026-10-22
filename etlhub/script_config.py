"""Plugs etlhub's config into etl/scripts/config.py, which on its own is the CLI version (environment / .env only).

Imported by etlhub/__init__.py, so every etlhub process (API, worker, tests) has it before any ETL script runs.
"""
import os

from etlhub.core.config import get_settings

# Both read before etl/scripts/config.py runs load_dotenv, which copies the root .env into os.environ:
# - DHIS_ENV_FALLBACK only counts from the real process environment, a .env line must not enable it;
# - Settings gives env vars priority over its env file: built later, ENV_FILE=.env.debug would lose to the root .env.
_ENV_FALLBACK = os.getenv("DHIS_ENV_FALLBACK", "").lower() == "true"
get_settings()

from etl.scripts import config  # noqa: E402

class DHIS2SessionError(RuntimeError):
    pass


def _get(key: str, default=None) -> str | None:
    """Editable keys (config_store.EDITABLE_KEYS): Redis only, loaded from .env at API start; absent = the default.
    A Redis error fails the job instead of silently running on .env values. Other keys: the environment / .env."""
    # Imported here, not at module level: this module loads with the etlhub package, before tests mock redis.
    from etlhub.infrastructure.config_store import CONFIG_KEY, EDITABLE_KEYS
    from etlhub.infrastructure.redis_client import get_redis
    if key in EDITABLE_KEYS:
        value = get_redis().hget(CONFIG_KEY, key)
        return value.strip() if value is not None else default
    return os.getenv(key, default)


def _dhis2_credential(field: str, env_key: str) -> str | None:
    """DHIS2 URL/token from the etlui login (Redis). .env only with DHIS_ENV_FALLBACK=true in the process environment."""
    from etlhub.infrastructure.auth_store import get_credential
    credential = get_credential()
    if credential:
        return credential[field]
    if _ENV_FALLBACK:
        return os.getenv(env_key)
    raise DHIS2SessionError("No active DHIS2 session (expired, logged out or Redis unavailable). Log in again in etlui.")


config._get, config._dhis2_credential = _get, _dhis2_credential
