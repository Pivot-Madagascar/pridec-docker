import uuid
from typing import Any

from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.task_launcher import TaskLauncher
from etlhub.domain.exceptions import JobNotFoundError
from etlhub.domain.schemas.forecast import ForecastParams


class ForecastService:
    def __init__(self, task_launcher: TaskLauncher, job_repo: JobRepository):
        self._task_launcher = task_launcher
        self._job_repo = job_repo

    def launch(self, params: ForecastParams, webhook_url: str | None = None) -> str:
        job_id = f"forecast_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("forecast", job_id, params={
            "config_valid_path": params.config_valid_path,
            "input_valid_path": params.input_valid_path,
            "polygon_valid_path": params.polygon_valid_path,
        }, webhook_url=webhook_url)
        return job_id

    def get_status(self, job_id: str) -> dict[str, Any]:
        status = self._job_repo.get(job_id)
        if status is not None:
            return status
        from etlhub.core.config import get_settings
        status = self._job_repo.load_from_file(job_id, get_settings().logs_dir)
        if status is not None:
            return status
        raise JobNotFoundError(f"Job not found: {job_id}")