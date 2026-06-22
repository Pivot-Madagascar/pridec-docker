import contextlib
import io
import sys
from pathlib import Path

from etlhub.core.config import get_settings
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


class ETLException(Exception):
    pass


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


def run_import_gee(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            import_gee()
        except Exception as e:
            raise ETLException(f"import_gee failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_import_pivot_com(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            import_pivot_com()
        except Exception as e:
            raise ETLException(f"import_pivot_com failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_import_pivot_csb(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            import_pivot_csb()
        except Exception as e:
            raise ETLException(f"import_pivot_csb failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_fetch_climate(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            fetch_climate()
        except Exception as e:
            raise ETLException(f"fetch_climate failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_fetch_disease(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            fetch_disease()
        except Exception as e:
            raise ETLException(f"fetch_disease failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_fetch_geojson(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            fetch_geojson()
        except Exception as e:
            raise ETLException(f"fetch_geojson failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_build_analytics(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            build_analytics()
        except Exception as e:
            raise ETLException(f"build_analytics failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_post_forecast(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            post_forecast()
        except Exception as e:
            raise ETLException(f"post_forecast failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_calc_csb_alerts(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            calc_csb_alerts()
        except Exception as e:
            raise ETLException(f"calc_csb_alerts failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())


def run_update_key(job_store=None, job_id=None) -> None:
    with capture_stdout(job_id=job_id) as buf:
        try:
            update_key()
        except Exception as e:
            raise ETLException(f"update_key failed: {e}") from e
    if job_store and job_id:
        job_store.save_logs(job_id, buf.getvalue())
