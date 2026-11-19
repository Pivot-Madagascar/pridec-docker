"""GET /api/tracking/etl-logs/{job_id}: logs plus the job status, for the tracking page."""
import pytest

from types import SimpleNamespace

from etlhub.application.use_cases.tracking_service import TrackingService
from etlhub.domain.exceptions import JobNotFoundError


# The current mode launched every job. Not tests.conftest.OpenGate: importing tests.conftest re-runs it (a second redis mock).
def open_gate():
    return SimpleNamespace(current_mode=lambda: "production", has_job=lambda job_id: True)


JOB = "import_gee_1234abcd"


def test_logs_come_with_status_and_message(job_store):
    job_store.set(JOB, {"status": "error", "message": "boom"})
    job_store.append_logs(JOB, "line 1\nline 2")

    log = TrackingService(None, job_store, open_gate()).get_etl_logs(JOB)

    assert (log.status, log.message, log.logs) == ("error", "boom", "line 1\nline 2")


def test_running_job_without_logs_yet_is_not_a_404(job_store):
    job_store.set(JOB, {"status": "running"})

    log = TrackingService(None, job_store, open_gate()).get_etl_logs(JOB)

    assert log.status == "running" and log.logs is None


def test_unknown_job_is_not_found(job_store):
    with pytest.raises(JobNotFoundError):
        TrackingService(None, job_store, open_gate()).get_etl_logs(JOB)


def test_a_job_of_the_other_mode_is_not_found(job_store):
    job_store.set(JOB, {"status": "success"})
    job_store.append_logs(JOB, "launched in the other mode")
    other_mode = SimpleNamespace(current_mode=lambda: "test", has_job=lambda job_id: False)

    with pytest.raises(JobNotFoundError):
        TrackingService(None, job_store, other_mode).get_etl_logs(JOB)


class Requests:
    def __init__(self, logs):
        self.logs = logs

    def list_recent(self, limit, endpoint, mode=None):
        self.mode = mode
        return self.logs

    def get(self, request_id):
        return next((log for log in self.logs if log["request_id"] == request_id), None)


def _log(request_id, job_id=None):
    return {"request_id": request_id, "method": "POST", "url": "/x", "status_code": 202 if job_id else 200,
            "duration_ms": 1.0, "job_id": job_id}


def test_job_launches_show_only_once_the_job_ended(job_store):
    for job_id, status in [("import_gee_00000001", "running"), ("import_gee_00000002", "success"),
                           ("import_gee_00000003", "pending")]:
        job_store.set(job_id, {"status": status})
    logs = [_log("r1", "import_gee_00000001"), _log("r2", "import_gee_00000002"), _log("r3", "import_gee_00000003"),
            _log("r4"), _log("r5", "import_gee_00000009")]  # r5: job record expired

    requests = Requests(logs)
    shown = TrackingService(requests, job_store, open_gate()).list_requests()

    assert [(r.request_id, r.job_status) for r in shown] == [("r2", "success"), ("r4", None), ("r5", None)]
    assert requests.mode == "production"  # the requests of the current mode only


def test_a_request_of_the_other_mode_is_not_found(job_store):
    requests = Requests([{**_log("p"), "mode": "production"}, {**_log("legacy")}, {**_log("t"), "mode": "test"}])
    service = TrackingService(requests, job_store, open_gate())

    assert service.get_request("p").request_id == "p"
    for other in ("t", "legacy"):  # test mode, or recorded before the mode was
        with pytest.raises(JobNotFoundError):
            service.get_request(other)
