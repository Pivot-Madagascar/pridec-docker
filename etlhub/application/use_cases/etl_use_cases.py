import contextlib
import io
import sys
from pathlib import Path

from etlhub.core.config import get_settings
from etlhub.domain.exceptions import ETLException
from etl.scripts.import_gee import import_gee
from etl.scripts.import_pivot_COM import import_pivot_com
from etl.scripts.import_pivot_CSB import import_pivot_csb
from etl.scripts.fetch_pridec_climate import fetch_climate
from etl.scripts.fetch_pridec_disease import fetch_disease
from etl.scripts.fetch_pridec_geojson import fetch_geojson
from etl.scripts.build_analytics import build_analytics
from etl.scripts.post_forecast import post_forecast
from etl.scripts.calc_CSB_alerts import calc_csb_alerts
from etl.scripts.update_pridec_key import update_key


class _JobLogger:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self._buf = io.StringIO()
        self._file_path = self._log_path()

    def _log_path(self) -> Path:
        settings = get_settings()
        log_dir = Path(settings.logs_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / f"{self.job_id}.log"

    def write(self, text: str) -> int:
        self._buf.write(text)
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

    def flush(self) -> None:
        self._buf.flush()
        try:
            with open(self._file_path, 'a') as f:
                f.flush()
        except Exception:
            pass

    @property
    def closed(self) -> bool:
        return False

    def writelines(self, lines) -> None:
        text = ''.join(lines)
        self.write(text)

    def getvalue(self) -> str:
        return self._buf.getvalue()


@contextlib.contextmanager
def capture_stdout(job_id: str | None = None):
    if job_id:
        logger = _JobLogger(job_id)
        with contextlib.redirect_stdout(logger), contextlib.redirect_stderr(logger):
            yield logger
    else:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            yield buf


def _execute_etl_job(fn, job_store=None, job_id=None, name=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            fn()
        except Exception as e:
            raise ETLException(f"{name} failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_import_gee(job_store=None, job_id=None) -> None:
    _execute_etl_job(import_gee, job_store=job_store, job_id=job_id, name="import_gee")


def run_import_pivot_com(job_store=None, job_id=None) -> None:
    _execute_etl_job(import_pivot_com, job_store=job_store, job_id=job_id, name="import_pivot_com")


def run_import_pivot_csb(job_store=None, job_id=None) -> None:
    _execute_etl_job(import_pivot_csb, job_store=job_store, job_id=job_id, name="import_pivot_csb")


def run_fetch_climate(job_store=None, job_id=None) -> None:
    _execute_etl_job(fetch_climate, job_store=job_store, job_id=job_id, name="fetch_climate")


def run_fetch_disease(job_store=None, job_id=None) -> None:
    _execute_etl_job(fetch_disease, job_store=job_store, job_id=job_id, name="fetch_disease")


def run_fetch_geojson(job_store=None, job_id=None) -> None:
    _execute_etl_job(fetch_geojson, job_store=job_store, job_id=job_id, name="fetch_geojson")


def run_build_analytics(job_store=None, job_id=None) -> None:
    _execute_etl_job(build_analytics, job_store=job_store, job_id=job_id, name="build_analytics")


def run_post_forecast(job_store=None, job_id=None) -> None:
    _execute_etl_job(post_forecast, job_store=job_store, job_id=job_id, name="post_forecast")


def run_calc_csb_alerts(job_store=None, job_id=None) -> None:
    _execute_etl_job(calc_csb_alerts, job_store=job_store, job_id=job_id, name="calc_csb_alerts")


def run_update_key(job_store=None, job_id=None) -> None:
    _execute_etl_job(update_key, job_store=job_store, job_id=job_id, name="update_key")
