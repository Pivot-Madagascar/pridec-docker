import contextlib
import io
import logging
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir
from etlhub.domain.exceptions import ETLException
from etlhub.domain.interfaces.event_publisher import EventPublisher
from etlhub.domain.interfaces.fetched_imports import FetchedImports
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.webhook_notifier import WebhookNotifier
from etlhub.application.use_cases.validation_use_cases import validate_input_files
from etlhub.application.use_cases.gee_import import import_gee  # one post per variable, its state kept
from etlhub.application.use_cases.calc_alerts import calc_orgunit_alerts  # etlhub's copy of the CLI script
from etlhub.application.use_cases.fetch_pivot import import_pivot_com, import_pivot_csb, post_pivot_imports
from etl.scripts.fetch_pridec_climate import fetch_climate
from etl.scripts.fetch_pridec_disease import fetch_disease
from etl.scripts.fetch_pridec_geojson import fetch_geojson
from etlhub.application.use_cases.build_analytics import build_analytics
from etlhub.application.use_cases.post_forecast import post_forecast
from etl.scripts.update_pridec_key import update_key

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
    "calc_orgunit_alerts": (calc_orgunit_alerts, "org unit alerts calculation"),
    "post_forecast": (post_forecast, "forecast publication"),  # a Celery job since 2026-11-24 (was synchronous)
    # Celery jobs since 2026-11-27 (were run inline by the API); launched by AnalyticsService after its own checks.
    "update_key": (update_key, "PRIDE-C key update"),
    "approve_imports": (post_pivot_imports, "imports approval"),
}
# The jobs that keep their data or state in FetchedImports: run_etl_job passes them the worker's adapter (`imports`).
WITH_FETCHED_IMPORTS = {"import_gee", "import_pivot_com", "import_pivot_csb", "approve_imports"}


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


def _execute_etl_job(fn, log: _JobLogger, name: str, **kwargs):
    """The scripts read DRYRUN through script_config._get: the mode the job runs in (DRYRUN = TEST MODE).
    Returns the job function's result: a string is its end message (post_forecast's, approve_imports')."""
    # etl/scripts/config.setup_logging() (basicConfig(force=True)) binds the root handlers to this job's log: put back
    # the process's own after the job, or every later root warning lands in the last job's log.
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            return fn(**kwargs)
        except Exception as e:
            raise ETLException(f"{name} failed: {_reason(e)}") from e
        finally:
            root.handlers[:] = handlers
            root.setLevel(level)


def _reason(e: Exception) -> str:
    """str(e), else the `errors` list of etl.scripts.validate_inputs.ValidationError (raised without a message)."""
    return str(e) or "\n".join(getattr(e, "errors", None) or []) or type(e).__name__


def run_etl_job(task_type: str, job_store: JobRepository, job_id: str, events: EventPublisher,
                imports: FetchedImports, **kwargs):
    fn = ETL_JOBS[task_type][0]
    if task_type in WITH_FETCHED_IMPORTS:
        kwargs["imports"] = imports
    with _into_mode_folder(task_type):
        return _execute_etl_job(fn, _JobLogger(job_store, job_id, events), task_type, **kwargs)


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


def notify_webhook(webhook_url: str | None, job_id: str, status: str, message: str, webhooks: WebhookNotifier) -> None:
    """POSTs {job_id, status, message, logs_url} to webhook_url, if any. Failures are ignored (logged by the adapter)."""
    if not webhook_url:
        return
    webhooks.post(webhook_url, job_id, {
        "job_id": job_id,
        "status": status,
        "message": message,
        "logs_url": f"/api/tracking/etl-logs/{job_id}",
    })
