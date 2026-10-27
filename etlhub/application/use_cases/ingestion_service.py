import logging
import uuid

from etl.scripts.check_import_availability import availability_plan
from etlhub.application.use_cases.availability_service import import_params
from etlhub.domain.interfaces.task_launcher import TaskLauncher
from etlhub.domain.pipeline import IMPORT_TASKS

logger = logging.getLogger(__name__)


class IngestionService:
    """Queues any Celery ETL job (imports, fetches, build_analytics, validate_inputs)."""

    def __init__(self, task_launcher: TaskLauncher, plan=availability_plan):
        self._task_launcher = task_launcher
        self._plan = plan

    def launch(self, task_type: str, webhook_url: str | None = None, confirm: bool = False, **kwargs) -> str:
        job_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        params = self._import_params(task_type) if task_type in IMPORT_TASKS else None
        self._task_launcher.launch(task_type, job_id, webhook_url=webhook_url, confirm=confirm, carry_over=params, **kwargs)
        return job_id

    def _import_params(self, task_type: str) -> dict[str, dict] | None:
        """The current parameters of the three imports: journaled with the launch, compared to carry the others over
        if it starts a pass (cycle-passes.md § 11). None never blocks the launch: the job fails on its own if PARENT_OU
        or the session is missing; such a launch just cannot be carried over, nor carry anything."""
        try:
            return import_params(self._plan())
        except Exception as e:
            logger.warning("Parameters of %s not recorded: %s", task_type, e)
            return None
