from etlhub.domain.interfaces.request_tracker import RequestTrackerProtocol
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.schemas.tracking import RequestLog, ETLLog
from etlhub.domain.exceptions import JobNotFoundError

# A job launch (202 Accepted) only matters once its job ended: hidden from the list until then.
_UNFINISHED = {"pending", "running"}


class TrackingService:
    def __init__(self, request_tracker: RequestTrackerProtocol, job_repo: JobRepository):
        self._request_tracker = request_tracker
        self._job_repo = job_repo

    def _with_job_status(self, log: dict) -> dict:
        """job_status from the job record (Redis, 24 h): None without a job_id or once it expired.

        A killed worker leaves its job "running" until DELETE /pipeline/lock sets it to error.
        """
        job = self._job_repo.get(log["job_id"]) if log.get("job_id") else None
        return {**log, "job_status": job.get("status") if job else None}

    def list_requests(self, limit: int = 50, endpoint: str | None = None) -> list[RequestLog]:
        logs = (self._with_job_status(log) for log in self._request_tracker.list_recent(limit, endpoint))
        return [RequestLog(**log) for log in logs if log["job_status"] not in _UNFINISHED]

    def get_request(self, request_id: str) -> RequestLog:
        log = self._request_tracker.get(request_id)
        if log is None:
            raise JobNotFoundError(f"Request not found: {request_id}")
        return RequestLog(**self._with_job_status(log))

    def get_etl_logs(self, job_id: str) -> ETLLog:
        """Logs and, while the job record exists (24 h), its status and message."""
        logs = self._job_repo.get_logs(job_id)
        job = self._job_repo.get(job_id) or {}
        if logs is None and not job:
            raise JobNotFoundError(f"ETL logs not found for this job_id: {job_id}")
        return ETLLog(job_id=job_id, status=job.get("status"), message=job.get("message"), logs=logs)