"""build_analytics as etlhub runs it (etl/scripts/build_analytics.py, the job's runner): DRYRUN = TEST MODE, the login's
DHIS2, and the library's progress in the job's log. pivot_dhis_tools.launch_analytics is replaced: no DHIS2 call."""
import logging

import pytest

from etl.scripts import build_analytics as script
from etlhub.application.use_cases import etl_use_cases
from etlhub.core.job_context import pipeline_test_mode
from etlhub.infrastructure import auth_store, etl_events, redis_client

CREDENTIAL = {"url": "https://dhis2.test", "token": "d2pat_login"}


class _Redis:  # the editable config: nothing set, the scripts take their defaults
    def hget(self, _key, _field):
        return None


@pytest.fixture
def run_job(job_store, monkeypatch):
    monkeypatch.setattr(redis_client, "get_redis", lambda: _Redis())
    monkeypatch.setattr(auth_store, "get_credential", lambda: CREDENTIAL)
    calls = []

    def launch_analytics(**kw):  # what pivot_dhis_tools logs while it waits for DHIS2
        calls.append(kw)
        logging.getLogger("pivot_dhis_tools.launch_analytics").debug("Latest status: Analytics tables updated 40%")

    monkeypatch.setattr(script, "launch_analytics", launch_analytics)

    def run(test_mode: bool) -> str:
        token = pipeline_test_mode.set(test_mode)  # as _run_task does: the launcher's mode
        try:
            etl_use_cases.run_etl_job("build_analytics", job_store, "build_analytics_1", etl_events)
        finally:
            pipeline_test_mode.reset(token)
        return job_store.get_logs("build_analytics_1") or ""

    return run, calls


def test_test_mode_builds_nothing(run_job):
    run, calls = run_job

    log = run(test_mode=True)

    assert calls == []
    assert "DRY RUN - analytics tables will not be built" in log


def test_production_builds_on_the_login_s_dhis2_and_shows_the_progress(run_job):
    run, calls = run_job

    log = run(test_mode=False)

    assert calls == [{"dhis_url": "https://dhis2.test", "token": "d2pat_login"}]
    assert "Latest status: Analytics tables updated 40%" in log  # DEBUG in the library, shown in the job's log
