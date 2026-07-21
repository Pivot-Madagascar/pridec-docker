from dotenv import load_dotenv
import os
from etlhub.infrastructure.config_store import ConfigStore

load_dotenv(override=False)

_store = ConfigStore()
_EDITABLE_KEYS = {"DHIS_URL", "DHIS_TOKEN", "PARENT_OU", "OU_LEVEL", "DISEASE_CODE", "DRYRUN", "LOG_LEVEL"}

def _get(key: str, default=None) -> str | None:
    if key in _EDITABLE_KEYS:
        redis_config = _store.get_all()
        if key in redis_config:
            return redis_config[key]
    return os.getenv(key, default)

def get_dry_run() -> bool:
    return _get('DRYRUN', 'true').lower() == 'true'

def get_log_level() -> str:
    return _get('LOG_LEVEL', 'INFO').upper()

def get_dhis_url() -> str | None:
    url = _get('DHIS_URL')
    return url.rstrip('/') if url else None

def get_dhis_token() -> str | None:
    return _get('DHIS_TOKEN')

def get_parent_ou() -> str | None:
    return _get('PARENT_OU')

def get_ou_level() -> str | None:
    return _get('OU_LEVEL')

def get_disease_code() -> str | None:
    return _get('DISEASE_CODE')

def get_gee_variables() -> list[str]:
    configured = [v.strip() for v in os.environ.get("GEE_VARIABLES", "").split(",") if v.strip()]
    if configured:
        return configured
    from pridec_gee import AVAILABLE_VARIABLES
    return list(AVAILABLE_VARIABLES)

DHIS_USER = os.getenv('DHIS_USER')
DHIS_PWD = os.getenv('DHIS_PWD')
PIVOT_URL = os.environ.get('PIVOT_URL')
if PIVOT_URL is not None:
    PIVOT_URL = PIVOT_URL.rstrip('/')
PIVOT_TOKEN = os.environ.get('PIVOT_TOKEN')
GEE_PROJECT = os.environ.get('GEE_PROJECT')
GEE_SERVICE_ACCOUNT = os.environ.get('GEE_SERVICE_ACCOUNT')

def setup_logging():
    import logging
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        datefmt="%Y-%m-%dT%H:%M:%S", force=True,
    )

def check_envvars(required_vars: dict):
    for name, value in required_vars.items():
        if value is None or value == "":
            raise EnvironmentError(f"Required environment variable '{name}' is missing. Verify your `.env` file.")
    return

LOG_LEVEL = get_log_level()