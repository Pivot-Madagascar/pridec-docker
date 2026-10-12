import uuid

from etlhub.application.use_cases.etl_use_cases import notify_webhook, run_etl_job
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.exceptions import ETLException
from etlhub.domain.schemas import ETLResponse


class AnalyticsService:
    """post_forecast and update_key: run synchronously, inside the pipeline gate."""

    def __init__(self, job_repo: JobRepository, gate: PipelineGate):
        self._job_repo = job_repo
        self._gate = gate

    def _run(self, task_type: str, message: str, webhook_url: str | None, confirm: bool) -> ETLResponse:
        job_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        with self._gate.run(task_type, job_id, confirm):  # PipelineBlockedError propagates as is
            try:
                run_etl_job(task_type, self._job_repo, job_id)
            except ETLException as e:
                raise ETLException(f"{task_type} failed: {e}") from e
        notify_webhook(webhook_url, job_id, "success", message)
        return ETLResponse(status="success", message=message, job_id=job_id, webhook_url=webhook_url)

    def post_forecast(self, webhook_url: str | None = None, confirm: bool = False) -> ETLResponse:
        return self._run("post_forecast", "Forecast posted successfully", webhook_url, confirm)

    def update_key(self, webhook_url: str | None = None, confirm: bool = False) -> ETLResponse:
        return self._run("update_key", "Key updated successfully", webhook_url, confirm)
