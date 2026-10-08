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
