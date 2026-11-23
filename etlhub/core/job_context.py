from contextvars import ContextVar
from pathlib import Path

# The fixed configuration of the job's pass (CheckpointStore.pass_config, PASS_CONFIG), handed to a Celery job with its
# launch: what script_config._get reads for PASS_KEYS. None outside a Celery job (the store's active pass then).
job_pass_config: ContextVar[dict | None] = ContextVar("job_pass_config", default=None)
# Script config key -> PASS_CONFIG column (pass-config.md). DRYRUN is the mode (script_config), the DHIS2 URL the login's.
PASS_KEYS = {"GEE_VARIABLES": "gee_variables", "PARENT_OU": "parent_ou", "LOG_LEVEL": "log_level"}

# Test mode of the request or job being served: the user's choice, kept in their session (get_current_user sets it),
# handed to a Celery job with its launch. None outside them.
pipeline_test_mode: ContextVar[bool | None] = ContextVar("pipeline_test_mode", default=None)


def current_test_mode() -> bool:
    """The mode of the request or job being served; test outside them, the mode a new session starts in."""
    value = pipeline_test_mode.get()
    return True if value is None else value


def work_dir(root: str | Path, name: str, test_mode: bool) -> Path:
    """input/ or output/ of a mode under `root`: <root>/<name> in production (the CLI's), <root>/test/<name> in test."""
    return Path(root) / "test" / name if test_mode else Path(root) / name
