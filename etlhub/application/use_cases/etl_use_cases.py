import contextlib
import io
import logging
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import httpx

from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir
from etlhub.domain.exceptions import ETLException
from etlhub.domain.interfaces.event_publisher import EventPublisher
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.application.use_cases.validation_use_cases import validate_input_files
from etl.scripts.import_gee import import_gee
from etlhub.application.use_cases.fetch_pivot import import_pivot_com, import_pivot_csb, post_pivot_imports
from etl.scripts.fetch_pridec_climate import fetch_climate
from etl.scripts.fetch_pridec_disease import fetch_disease
from etl.scripts.fetch_pridec_geojson import fetch_geojson
from etlhub.application.use_cases.build_analytics import build_analytics
from etlhub.application.use_cases.post_forecast import post_forecast
from etl.scripts.update_pridec_key import update_key

logger = logging.getLogger(__name__)

# Jobs run by the Celery worker: task_type -> (function, label of the job status messages).
ETL_JOBS = {
    "import_gee": (import_gee, "GEE import"),
    "import_pivot_com": (import_pivot_com, "Pivot COM import"),
    "import_pivot_csb": (import_pivot_csb, "Pivot CSB import"),
    "fetch_climate": (fetch_climate, "climate data fetch"),
    "fetch_disease": (fetch_disease, "disease data fetch"),
    "fetch_geojson": (fetch_geojson, "GeoJSON fetch"),
    "build_analytics": (build_analytics, "analytics build"),
    "validate_inputs": (validate_input_files, "validate inputs"),
}
# Run synchronously by the API (AnalyticsService).
SYNC_JOBS = {"post_forecast": post_forecast, "update_key": update_key, "approve_imports": post_pivot_imports}


class _JobLogger(io.StringIO):
    """Job stdout/stderr: appended to the job logs (Redis and logs/{job_id}.log) and published live."""

    def __init__(self, job_store: JobRepository, job_id: str, events: EventPublisher):
        super().__init__()
        self.job_store = job_store
        self.job_id = job_id
        self.events = events

    def write(self, text: str) -> int:
        self.job_store.append_logs(self.job_id, text)  # history first: a client connecting now loses nothing
        try:
            level = "INFO"
            upper = text.upper()
            if "ERROR" in upper:
                level = "ERROR"
            elif "WARNING" in upper or "WARN" in upper:
                level = "WARNING"
            elif "DEBUG" in upper:
                level = "DEBUG"
            self.events.publish_log(self.job_id, level, text)
        except Exception:
            pass
        return len(text)


def _execute_etl_job(fn, log: _JobLogger, name: str, **kwargs) -> None:
    """The scripts read DRYRUN through script_config._get: the mode the job runs in (DRYRUN = TEST MODE)."""
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            fn(**kwargs)
        except Exception as e:
            raise ETLException(f"{name} failed: {_reason(e)}") from e


def _reason(e: Exception) -> str:
    """str(e), else the `errors` list of etl.scripts.validate_inputs.ValidationError (raised without a message)."""
    return str(e) or "\n".join(getattr(e, "errors", None) or []) or type(e).__name__


def run_etl_job(task_type: str, job_store: JobRepository, job_id: str, events: EventPublisher, **kwargs) -> None:
    fn = SYNC_JOBS[task_type] if task_type in SYNC_JOBS else ETL_JOBS[task_type][0]
    with _into_mode_folder(task_type):
        _execute_etl_job(fn, _JobLogger(job_store, job_id, events), task_type, **kwargs)


# The file each fetch_* script of etl/ writes into os.getcwd()/input (no parameter): the production folder.
FETCH_OUTPUTS = {"fetch_climate": "climate_data.json", "fetch_disease": "disease_data.json",
                 "fetch_geojson": "orgUnit_poly.geojson"}


@contextlib.contextmanager
def _into_mode_folder(task_type: str) -> Iterator[None]:
    """A test-mode fetch: its file goes to test/input; production's in ./input is put back as it was, even on failure.

    ponytail: safe only because one job runs at a time, both modes together (a production job would otherwise see
    the test file meanwhile). An input-folder setting in the three scripts (etl/) would remove the shuffle.
    """
    name = FETCH_OUTPUTS.get(task_type)
    if name is None or not current_test_mode():
        yield
        return
    written = Path(os.getcwd()) / "input" / name
    aside = written.with_name(f".{name}.production")
    if written.exists():
        os.replace(written, aside)
    try:
        yield
        if written.exists():
            target = work_dir(get_settings().data_dir, "input", True) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(written, target)
    finally:
        written.unlink(missing_ok=True)  # what a failed fetch left
        if aside.exists():
            os.replace(aside, written)


def notify_webhook(webhook_url: str | None, job_id: str, status: str, message: str) -> None:
    """POSTs {job_id, status, message, logs_url} to webhook_url, if any. Failures are ignored."""
    if not webhook_url:
        return
    try:
        # httpx does not follow redirects: the host checked at launch is the only one called.
        httpx.post(webhook_url, json={
            "job_id": job_id,
            "status": status,
            "message": message,
            "logs_url": f"/api/tracking/etl-logs/{job_id}",
        }, timeout=10)
    except Exception as e:  # the host only: the path or query of a webhook may carry a token
        logger.warning("Webhook of %s to %s failed: %s", job_id, httpx.URL(webhook_url).host, type(e).__name__)
