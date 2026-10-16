import contextlib
import io
from pathlib import Path

import httpx

from etlhub.core.config import get_settings
from etlhub.domain.exceptions import ETLException
from etlhub.application.use_cases.validation_use_cases import validate_input_files
from etl.scripts.import_gee import import_gee
from etl.scripts.import_pivot_COM import import_pivot_com
from etl.scripts.import_pivot_CSB import import_pivot_csb
from etl.scripts.fetch_pridec_climate import fetch_climate
from etl.scripts.fetch_pridec_disease import fetch_disease
from etl.scripts.fetch_pridec_geojson import fetch_geojson
from etl.scripts.build_analytics import build_analytics
from etl.scripts.post_forecast import post_forecast
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
}
# Run synchronously by the API (AnalyticsService).
SYNC_JOBS = {"post_forecast": post_forecast, "update_key": update_key}


class _JobLogger(io.StringIO):
    """Job stdout/stderr: kept in memory, appended to logs/{job_id}.log and published live."""

    def __init__(self, job_id: str):
        super().__init__()
        self.job_id = job_id
        log_dir = Path(get_settings().logs_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = log_dir / f"{job_id}.log"

    def write(self, text: str) -> int:
        super().write(text)
        try:
            with open(self._file_path, 'a') as f:
                f.write(text)
        except Exception:
            pass
        try:
            from etlhub.api.etl_events import get_etl_event_manager
            level = "INFO"
            upper = text.upper()
            if "ERROR" in upper:
                level = "ERROR"
            elif "WARNING" in upper or "WARN" in upper:
                level = "WARNING"
            elif "DEBUG" in upper:
                level = "DEBUG"
            get_etl_event_manager().publish_log(self.job_id, level, text)
        except Exception:
            pass
        return len(text)


def _execute_etl_job(fn, job_store, job_id: str, name: str, **kwargs) -> None:
    buf = _JobLogger(job_id)
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            fn(**kwargs)
        except Exception as e:
            raise ETLException(f"{name} failed: {e}") from e
    job_store.save_logs(job_id, buf.getvalue())


def run_etl_job(task_type: str, job_store, job_id: str, **kwargs) -> None:
    fn = SYNC_JOBS[task_type] if task_type in SYNC_JOBS else ETL_JOBS[task_type][0]
    _execute_etl_job(fn, job_store, job_id, task_type, **kwargs)


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
    except Exception:
        pass
