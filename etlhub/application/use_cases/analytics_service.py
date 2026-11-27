import uuid

from etlhub.application.use_cases.fetch_pivot import not_fetched
from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.interfaces.task_launcher import TaskLauncher
from etlhub.domain.exceptions import PipelineBlockedError


class AnalyticsService:
    """update_key and approve_imports (posts the chosen Pivot elements): their own checks, then a Celery job like any
    launch (since 2026-11-27; they ran inline in the API process before). Returns the job_id."""

    def __init__(self, task_launcher: TaskLauncher, gate: PipelineGate):
        self._task_launcher = task_launcher
        self._gate = gate

    def update_key(self, webhook_url: str | None = None, confirm: bool = False) -> str:
        if self._gate.default_dry_run():
            # Before the gate: a refusal writes nothing.
            raise PipelineBlockedError(
                "update_key cannot run in test mode: test mode is a dry run (DRYRUN = TEST MODE) and pivot_dhis_tools "
                "ignores its dryRun, it would write the PRIDE-C key to DHIS2 anyway. Update the key in production mode.")
        job_id = f"update_key_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("update_key", job_id, webhook_url=webhook_url, confirm=confirm)
        return job_id

    def approve_imports(self, elements: list[str], confirm: bool = False) -> str:
        """Posts the chosen fetched elements (none: nothing posted), then approve_imports is success (the job's end).
        The elements are journaled with the launch (launched event `params`, through carry_over)."""
        elements = list(dict.fromkeys(elements))
        if missing := not_fetched(elements):  # before the gate: a refusal writes nothing
            raise PipelineBlockedError(f"Not fetched in this pass: {', '.join(missing)}. Launch its Pivot import again first")
        job_id = f"approve_imports_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("approve_imports", job_id, confirm=confirm,
                                   carry_over={"approve_imports": {"elements": elements}}, elements=elements)
        return job_id
