"""Storage and notification failures are logged, never raised, and never loop back into the job's own log."""
import logging

import httpx
import pytest

from etlhub.application.use_cases import etl_use_cases
from etlhub.core.config import get_settings
from etlhub.infrastructure import etl_events, job_store


@pytest.fixture
def root_handlers_restored():
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


def test_redis_down_during_a_job_is_logged_and_the_line_still_reaches_the_log_file(monkeypatch, capfd, tmp_path,
                                                                                  root_handlers_restored):
    def redis_down():
        raise ConnectionError("redis down")

    monkeypatch.setattr(job_store, "get_redis", redis_down)
    monkeypatch.setattr(etl_events, "publish_log", lambda *args: None)
    monkeypatch.setattr(get_settings(), "logs_dir", str(tmp_path))
    store = job_store.JobStore()

    def job():
        # What etl/scripts/config.setup_logging() does at the start of each script: the root handler now writes to the
        # job's _JobLogger. A JobStore warning going through it would call append_logs again, endlessly.
        logging.basicConfig(level=logging.INFO, force=True)
        print("step 1")

    etl_use_cases._execute_etl_job(job, etl_use_cases._JobLogger(store, "import_gee_1", etl_events), "import_gee")

    assert (tmp_path / "import_gee_1.log").read_text() == "step 1\n"
    assert store.get("import_gee_1") is None
    err = capfd.readouterr().err  # JobStore logs to the real stderr, never into the job
    assert "JobStore.append_logs(import_gee_1) to Redis failed: redis down" in err
    assert "JobStore.get(import_gee_1) failed" in err


def test_a_failed_webhook_is_logged_with_its_host_only(monkeypatch, caplog):
    url = "https://hooks.example.org/x?token=s3cret"

    def refused(*args, **kwargs):
        raise httpx.ConnectError(f"cannot reach {url}")

    monkeypatch.setattr(etl_use_cases.httpx, "post", refused)

    etl_use_cases.notify_webhook(url, "import_gee_1", "success", "done")

    assert "Webhook of import_gee_1 to hooks.example.org failed: ConnectError" in caplog.text
    assert "s3cret" not in caplog.text
