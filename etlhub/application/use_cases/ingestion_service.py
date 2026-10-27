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
        params = current_import_params(self._plan) if task_type in IMPORT_TASKS else None
        self._task_launcher.launch(task_type, job_id, webhook_url=webhook_url, confirm=confirm, carry_over=params, **kwargs)
        return job_id


def current_import_params(plan=availability_plan) -> dict[str, dict] | None:
    """The current parameters of the three imports: journaled with a launch, compared to carry the imports over when a
    pass starts (cycle-passes.md § 11). None never blocks: the job fails on its own if PARENT_OU or the session is
    missing; such a launch just cannot be carried over, and a pass started then carries no import."""
    try:
        return import_params(plan())
    except Exception as e:
        logger.warning("Parameters of the imports not read: %s", e)
        return None
