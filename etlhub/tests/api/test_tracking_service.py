"""GET /api/tracking/etl-logs/{job_id}: logs plus the job status, for the tracking page."""
import pytest

from etlhub.application.use_cases.tracking_service import TrackingService
from etlhub.domain.exceptions import JobNotFoundError


class Jobs:
    def __init__(self, job=None, logs=None):
        self.job, self.logs = job, logs

    def get(self, job_id):
        return self.job

    def get_logs(self, job_id):
        return self.logs


def test_logs_come_with_status_and_message():
    service = TrackingService(None, Jobs({"status": "error", "message": "boom"}, "line 1\nline 2"))

    log = service.get_etl_logs("import_gee_1234abcd")

    assert (log.status, log.message, log.logs) == ("error", "boom", "line 1\nline 2")


def test_running_job_without_logs_yet_is_not_a_404():
    log = TrackingService(None, Jobs({"status": "running"}, None)).get_etl_logs("import_gee_1234abcd")

    assert log.status == "running" and log.logs is None


def test_unknown_job_is_not_found():
    with pytest.raises(JobNotFoundError):
        TrackingService(None, Jobs(None, None)).get_etl_logs("import_gee_1234abcd")


class Requests:
    def __init__(self, logs):
        self.logs = logs

    def list_recent(self, limit, endpoint):
        return self.logs


class JobsById:
    def __init__(self, statuses):
        self.statuses = statuses

    def get(self, job_id):
        return {"status": self.statuses[job_id]} if job_id in self.statuses else None


def _log(request_id, job_id=None):
    return {"request_id": request_id, "method": "POST", "url": "/x", "status_code": 202 if job_id else 200,
            "duration_ms": 1.0, "job_id": job_id}


def test_job_launches_show_only_once_the_job_ended():
    jobs = JobsById({"import_gee_00000001": "running", "import_gee_00000002": "success", "import_gee_00000003": "pending"})
    logs = [_log("r1", "import_gee_00000001"), _log("r2", "import_gee_00000002"), _log("r3", "import_gee_00000003"),
            _log("r4"), _log("r5", "import_gee_00000009")]  # r5: job record expired

    shown = TrackingService(Requests(logs), jobs).list_requests()

    assert [(r.request_id, r.job_status) for r in shown] == [("r2", "success"), ("r4", None), ("r5", None)]
