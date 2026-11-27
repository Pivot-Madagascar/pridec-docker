"""build_analytics as etlhub runs it (application/use_cases/build_analytics.py): DRYRUN = TEST MODE, the login's DHIS2,
no time limit (pivot_dhis_tools gave up after 15 min), and DHIS2's notifications in the job's log. DHIS2 is faked."""
import httpx
import pytest

from etlhub.application.use_cases import build_analytics as job
from etlhub.application.use_cases import etl_use_cases
from etlhub.core.job_context import pipeline_test_mode
from etlhub.domain.exceptions import ETLException
from etlhub.infrastructure import auth_store, etl_events, redis_client

CREDENTIAL = {"url": "https://dhis2.test", "token": "d2pat_login"}
STATUS = "/api/system/tasks/ANALYTICS_TABLE/m6ySYJZLJCD"  # as DHIS2 2.40 answered (logs/build_analytics_0b13c5f6.log)


class _Redis:  # the editable config: nothing set, the scripts take their defaults
    def hget(self, _key, _field):
        return None


def note(uid, message, level="INFO", completed=False):
    return {"uid": uid, "message": message, "level": level, "completed": completed}


@pytest.fixture
def run_job(job_store, monkeypatch):
    """run(polls, test_mode, endpoint) -> (log, requests sent); polls: the notification lists DHIS2 answers in turn."""
    monkeypatch.setattr(redis_client, "get_redis", lambda: _Redis())
    monkeypatch.setattr(auth_store, "get_credential", lambda: CREDENTIAL)
    monkeypatch.setattr(job, "POLL_SECONDS", 0)

    def run(polls=(), test_mode=False, endpoint=STATUS):
        sent, answers = [], iter(polls)

        def post(url, headers, timeout):
            sent.append(("POST", url, headers))
            return httpx.Response(200, json={"response": {"relativeNotifierEndpoint": endpoint}},
                                  request=httpx.Request("POST", url))

        def get(url, headers, timeout):
            sent.append(("GET", url, headers))
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            if isinstance(answer, int):  # an HTTP error status
                return httpx.Response(answer, request=httpx.Request("GET", url))
            return httpx.Response(200, json=answer, request=httpx.Request("GET", url))

        monkeypatch.setattr(job.httpx, "post", post)
        monkeypatch.setattr(job.httpx, "get", get)
        token = pipeline_test_mode.set(test_mode)  # as _run_task does: the launcher's mode
        try:
            etl_use_cases.run_etl_job("build_analytics", job_store, "build_analytics_1", etl_events, None)  # no FetchedImports
        finally:
            pipeline_test_mode.reset(token)
            log = job_store.get_logs("build_analytics_1") or ""
        return log, sent

    return run


def test_test_mode_builds_nothing(run_job):
    log, sent = run_job(test_mode=True)

    assert sent == []
    assert "DRY RUN - analytics tables will not be built" in log


def test_production_waits_for_dhis2_however_long_and_logs_each_new_message_once(run_job):
    # DHIS2 2.40 updates one notification in place (same uid, new message): seen on dhis2-pridec-test, 2026-11-23
    polls = ([[note("job", "Analytics table update process")]]
             + [[note("job", "[6/11] generating Category table")]] * 40
             + [[note("job", "[200/2799] in_In3EKQS6P2p_ax_2024_wT02C")]]
             + [[note("job", "Analytics tables updated: 00:04:56.441", completed=True)]])

    log, sent = run_job(polls)  # 43 polls of 30 s: 21.5 min, past the library's 15

    auth = {"Authorization": "ApiToken d2pat_login"}
    assert sent[0] == ("POST", "https://dhis2.test/api/33/resourceTables/analytics", auth)
    assert sent[1:] == [("GET", "https://dhis2.test" + STATUS, auth)] * 43
    messages = ["update process", "[6/11]", "[200/2799]", "tables updated: 00:04:56.441"]
    assert [log.count(m) for m in messages] == [1, 1, 1, 1]
    assert [log.index(m) for m in messages] == sorted(log.index(m) for m in messages)


def test_an_error_notification_fails_the_job(run_job):
    with pytest.raises(ETLException, match="Analytics table build failed: Disk full"):
        run_job([[note("a", "Disk full", level="ERROR")]])


def test_a_network_cut_or_a_dhis2_restart_is_waited_out(run_job):
    polls = [httpx.ConnectError("connection refused"), 503, [note("a", "Analytics tables updated", completed=True)]]

    log, sent = run_job(polls)

    assert len(sent) == 4  # the launch, then 3 polls: the job went on after the cut and the 503
    assert log.count("checking again in") == 2
    assert "Analytics table build completed" in log


def test_a_refused_status_request_fails_the_job(run_job):  # 4xx: the token or the task is gone, waiting won't help
    with pytest.raises(ETLException, match="401"):
        run_job([401])


def test_the_token_never_goes_to_a_status_url_dhis2_sends_elsewhere(run_job):
    with pytest.raises(ETLException, match="Unexpected analytics status endpoint"):
        run_job(endpoint="https://elsewhere.test/api/system/tasks/ANALYTICS_TABLE/x")
