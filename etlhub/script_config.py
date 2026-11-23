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
    from etlhub.core.job_context import PASS_KEYS, current_test_mode, job_pass_config
    from etlhub.infrastructure.config_store import CONFIG_KEY, EDITABLE_KEYS
    from etlhub.infrastructure.redis_client import get_redis
    if key == "DRYRUN":  # DRYRUN = TEST MODE (since 2026-11-23): the mode served (a job's: its launcher's); never .env
        return "true" if current_test_mode() else "false"
    if key in PASS_KEYS:  # fixed when the pass started (pass-config.md): the job's pass, else the active one
        config = job_pass_config.get()
        if config is None:
            from etlhub.infrastructure.checkpoint_store import get_checkpoint_store
            config = get_checkpoint_store().pass_config() or {}
        if (value := config.get(PASS_KEYS[key])) is not None:
            return value
        if key == "GEE_VARIABLES":  # never .env: every variable (no pass, or one from before 2026-11-20)
            return default
    if key in EDITABLE_KEYS:
        value = get_redis().hget(CONFIG_KEY, key)
        return value.strip() if value is not None else default
    return os.getenv(key, default)


def _dhis2_credential(field: str, env_key: str) -> str | None:
    """DHIS2 URL/token from the etlui login (Redis). .env only with DHIS_ENV_FALLBACK=true in the process environment."""
    from etlhub.infrastructure.auth_store import get_credential
    from etlhub.core.job_context import job_pass_config
    credential = get_credential()
    if credential:
        fixed = (job_pass_config.get() or {}).get("dhis_url")
        if fixed and credential["url"] != fixed:  # someone logged in to another DHIS2 since the launch
            raise DHIS2SessionError(f"This job's pass runs on {fixed}, the DHIS2 session is on {credential['url']}: "
                                    "log in to the pass's DHIS2 again")
        return credential[field]
    if _ENV_FALLBACK:
        return os.getenv(env_key)
    raise DHIS2SessionError("No active DHIS2 session (expired, logged out or Redis unavailable). Log in again in etlui.")


config._get, config._dhis2_credential = _get, _dhis2_credential
