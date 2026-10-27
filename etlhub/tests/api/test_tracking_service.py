"""GET /api/tracking/etl-logs/{job_id}: logs plus the job status, for the tracking page."""
import pytest

from etlhub.application.use_cases.tracking_service import TrackingService
from etlhub.domain.exceptions import JobNotFoundError


JOB = "import_gee_1234abcd"


def test_logs_come_with_status_and_message(job_store):
    job_store.set(JOB, {"status": "error", "message": "boom"})
    job_store.append_logs(JOB, "line 1\nline 2")

    log = TrackingService(None, job_store).get_etl_logs(JOB)

    assert (log.status, log.message, log.logs) == ("error", "boom", "line 1\nline 2")


def test_running_job_without_logs_yet_is_not_a_404(job_store):
    job_store.set(JOB, {"status": "running"})

    log = TrackingService(None, job_store).get_etl_logs(JOB)

    assert log.status == "running" and log.logs is None


def test_unknown_job_is_not_found(job_store):
    with pytest.raises(JobNotFoundError):
        TrackingService(None, job_store).get_etl_logs(JOB)


class Requests:
    def __init__(self, logs):
        self.logs = logs

    def list_recent(self, limit, endpoint):
        return self.logs


def _log(request_id, job_id=None):
    return {"request_id": request_id, "method": "POST", "url": "/x", "status_code": 202 if job_id else 200,
            "duration_ms": 1.0, "job_id": job_id}


def test_job_launches_show_only_once_the_job_ended(job_store):
    for job_id, status in [("import_gee_00000001", "running"), ("import_gee_00000002", "success"),
                           ("import_gee_00000003", "pending")]:
        job_store.set(job_id, {"status": status})
    logs = [_log("r1", "import_gee_00000001"), _log("r2", "import_gee_00000002"), _log("r3", "import_gee_00000003"),
            _log("r4"), _log("r5", "import_gee_00000009")]  # r5: job record expired

    shown = TrackingService(Requests(logs), job_store).list_requests()

    assert [(r.request_id, r.job_status) for r in shown] == [("r2", "success"), ("r4", None), ("r5", None)]
