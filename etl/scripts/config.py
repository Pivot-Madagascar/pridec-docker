from dotenv import load_dotenv
import os

load_dotenv(override=False)

# The CLI reads everything from the environment / .env (`-e` beats .env), never Redis.
# etlhub replaces these two functions at startup (etlhub/script_config.py): editable keys from Redis,
# DHIS2 URL/token from the etlui login. Keep their names and signatures.
def _get(key: str, default=None) -> str | None:
    return os.getenv(key, default)

def _dhis2_credential(field: str, env_key: str) -> str | None:
    return os.getenv(env_key)

def get_dry_run() -> bool:
    return _get('DRYRUN', 'true').lower() == 'true'

def get_log_level() -> str:
    return _get('LOG_LEVEL', 'INFO').upper()

def get_dhis_url() -> str | None:
    url = _dhis2_credential('url', 'DHIS_URL')
    return url.rstrip('/') if url else None

def get_dhis_token() -> str | None:
    return _dhis2_credential('token', 'DHIS_TOKEN')

def get_parent_ou() -> str | None:
    return _get('PARENT_OU')

def get_ou_level() -> str | None:
    return _get('OU_LEVEL')

def get_disease_code() -> str | None:
    return _get('DISEASE_CODE')

def get_gee_variables() -> list[str]:
    configured = [v.strip() for v in _get("GEE_VARIABLES", "").split(",") if v.strip()]
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
        level=getattr(logging, get_log_level(), logging.INFO),
        datefmt="%Y-%m-%dT%H:%M:%S", force=True,
    )

def check_envvars(required_vars: dict):
    for name, value in required_vars.items():
        if value is None or value == "":
            raise EnvironmentError(f"Required environment variable '{name}' is missing. Verify your `.env` file.")
    return

# Old module API (config.dryRun, config.DHIS_URL, `from config import DHIS_URL`...), read through the getters.
# `from config import X` freezes X at import: under etlhub, call the getters instead.
_LEGACY = {
    "dryRun": get_dry_run, "LOG_LEVEL": get_log_level, "DHIS_URL": get_dhis_url, "DHIS_TOKEN": get_dhis_token,
    "PARENT_OU": get_parent_ou, "OU_LEVEL": get_ou_level, "DISEASE_CODE": get_disease_code,
    "GEE_VARIABLES": get_gee_variables,
}

def __getattr__(name):
    if name in _LEGACY:
        return _LEGACY[name]()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
