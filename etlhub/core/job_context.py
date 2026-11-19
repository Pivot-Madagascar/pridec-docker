from contextvars import ContextVar
from pathlib import Path

# DRYRUN of the job running in this context (its launch's choice, else the default the gate gave): what the ETL
# scripts read through script_config._get("DRYRUN"). None outside a job: they read DRYRUN from Redis (.env).
job_dry_run: ContextVar[bool | None] = ContextVar("job_dry_run", default=None)

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
