import uuid

from etlhub.application.use_cases.etl_use_cases import run_post_forecast, run_update_key
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.task_launcher import TaskLauncher
from etlhub.domain.interfaces.webhook_notifier import WebhookNotifier
from etlhub.domain.exceptions import ETLException
from etlhub.domain.schemas import ETLResponse


class AnalyticsService:
    def __init__(self, task_launcher: TaskLauncher, job_repo: JobRepository, webhook_notifier: WebhookNotifier):
        self._task_launcher = task_launcher
        self._job_repo = job_repo
        self._webhook_notifier = webhook_notifier

    def build_analytics(self, webhook_url: str | None = None) -> str:
        job_id = f"build_analytics_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("build_analytics", job_id, webhook_url=webhook_url)
        return job_id

    def post_forecast(self, webhook_url: str | None = None) -> ETLResponse:
        job_id = f"post_forecast_{uuid.uuid4().hex[:8]}"
        try:
            run_post_forecast(job_store=self._job_repo, job_id=job_id)
            result = ETLResponse(status="success", message="Forecast posted successfully", job_id=job_id, webhook_url=webhook_url)
        except ETLException as e:
            raise ETLException(f"post_forecast failed: {e}") from e
        if webhook_url:
            self._webhook_notifier.send(webhook_url, job_id=job_id, status="success", message="Forecast posted successfully", logs_url=f"/api/tracking/etl-logs/{job_id}")
        return result

    def calc_csb_alerts(self, webhook_url: str | None = None) -> str:
        job_id = f"calc_csb_alerts_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("calc_csb_alerts", job_id, webhook_url=webhook_url)
        return job_id

    def update_key(self, webhook_url: str | None = None) -> ETLResponse:
        job_id = f"update_key_{uuid.uuid4().hex[:8]}"
        try:
            run_update_key(job_store=self._job_repo, job_id=job_id)
            result = ETLResponse(status="success", message="Key updated successfully", job_id=job_id, webhook_url=webhook_url)
        except ETLException as e:
            raise ETLException(f"update_key failed: {e}") from e
        if webhook_url:
            self._webhook_notifier.send(webhook_url, job_id=job_id, status="success", message="Key updated successfully", logs_url=f"/api/tracking/etl-logs/{job_id}")
        return result