from etlhub.domain.interfaces.request_tracker import RequestTrackerProtocol
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.schemas.tracking import RequestLog, ETLLog
from etlhub.domain.exceptions import JobNotFoundError


class TrackingService:
    def __init__(self, request_tracker: RequestTrackerProtocol, job_repo: JobRepository):
        self._request_tracker = request_tracker
        self._job_repo = job_repo

    def list_requests(self, limit: int = 50, endpoint: str | None = None) -> list[RequestLog]:
        return [
            RequestLog(**log)
            for log in self._request_tracker.list_recent(limit, endpoint)
        ]

    def get_request(self, request_id: str) -> RequestLog:
        log = self._request_tracker.get(request_id)
        if log is None:
            raise JobNotFoundError(f"Request not found: {request_id}")
        return RequestLog(**log)

    def get_etl_logs(self, job_id: str) -> ETLLog:
        logs = self._job_repo.get_logs(job_id)
        if logs is None:
            raise JobNotFoundError(f"ETL logs not found for this job_id: {job_id}")
        return ETLLog(job_id=job_id, logs=logs)