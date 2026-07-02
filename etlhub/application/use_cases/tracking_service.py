from etlhub.domain.interfaces.request_tracker import RequestTrackerProtocol
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.schemas.tracking import RequestLog, ETLLog


class TrackingService:
    def __init__(self, request_tracker: RequestTrackerProtocol, job_repo: JobRepository):
        self._request_tracker = request_tracker
        self._job_repo = job_repo

    def list_requests(self, limit: int = 50) -> list[RequestLog]:
        return [RequestLog(**log) for log in self._request_tracker.list_recent(limit)]

    def get_request(self, request_id: str) -> RequestLog:
        log = self._request_tracker.get(request_id)
        if log is None:
            raise ValueError("Request not found")
        return RequestLog(**log)

    def get_etl_logs(self, job_id: str) -> ETLLog:
        logs = self._job_repo.get_logs(job_id)
        if logs is None:
            raise ValueError("ETL logs not found for this job_id")
        return ETLLog(job_id=job_id, logs=logs)