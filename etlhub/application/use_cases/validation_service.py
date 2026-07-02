import uuid

from etlhub.domain.interfaces.task_launcher import TaskLauncher


class ValidationService:
    def __init__(self, task_launcher: TaskLauncher):
        self._task_launcher = task_launcher

    def validate_inputs(self, webhook_url: str | None = None, **kwargs) -> str:
        job_id = f"validate_inputs_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("validate_inputs", job_id, webhook_url=webhook_url, **kwargs)
        return job_id