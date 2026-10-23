import uuid

from etlhub.domain.interfaces.task_launcher import TaskLauncher


class IngestionService:
    """Queues any Celery ETL job (imports, fetches, build_analytics, validate_inputs)."""

    def __init__(self, task_launcher: TaskLauncher):
        self._task_launcher = task_launcher

    def launch(self, task_type: str, webhook_url: str | None = None, confirm: bool = False, **kwargs) -> str:
        job_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch(task_type, job_id, webhook_url=webhook_url, confirm=confirm, **kwargs)
        return job_id
