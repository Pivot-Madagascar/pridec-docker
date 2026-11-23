import uuid

from etlhub.application.use_cases.etl_use_cases import notify_webhook, run_etl_job
from etlhub.application.use_cases.fetch_pivot import not_fetched
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.interfaces.event_publisher import EventPublisher
from etlhub.domain.exceptions import ETLException, PipelineBlockedError
from etlhub.domain.schemas import ETLResponse

# Inline jobs running in this API process: whether the holder of the pipeline lock is still alive (DELETE /pipeline/lock).
# ponytail: one set per process, right with a single API process (run_server.py); several would need a shared registry.
RUNNING_INLINE: set[str] = set()


class AnalyticsService:
    """post_forecast, update_key and approve_imports (posts the chosen Pivot elements): run synchronously, inside the
    pipeline gate."""

    def __init__(self, job_repo: JobRepository, gate: PipelineGate, events: EventPublisher):
        self._job_repo = job_repo
        self._gate = gate
        self._events = events

    def _run(self, task_type: str, message: str, webhook_url: str | None, confirm: bool,
             params: dict | None = None) -> ETLResponse:
        """params: the job function's arguments, also kept in the journal (launched event)."""
        job_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        if task_type == "update_key" and self._gate.default_dry_run():
            # Before the gate: a refusal writes nothing.
            raise PipelineBlockedError(
                "update_key cannot run in test mode: test mode is a dry run (DRYRUN = TEST MODE) and pivot_dhis_tools "
                "ignores its dryRun, it would write the PRIDE-C key to DHIS2 anyway. Update the key in production mode.")
        with self._gate.run(task_type, job_id, confirm, params):  # PipelineBlockedError propagates as is
            RUNNING_INLINE.add(job_id)
            try:
                run_etl_job(task_type, self._job_repo, job_id, self._events, **(params or {}))
            except ETLException as e:
                raise ETLException(f"{task_type} failed: {e}") from e
            finally:
                RUNNING_INLINE.discard(job_id)
        notify_webhook(webhook_url, job_id, "success", message)
        return ETLResponse(status="success", message=message, job_id=job_id, webhook_url=webhook_url)

    def post_forecast(self, webhook_url: str | None = None, confirm: bool = False) -> ETLResponse:
        return self._run("post_forecast", "Forecast posted successfully", webhook_url, confirm)

    def update_key(self, webhook_url: str | None = None, confirm: bool = False) -> ETLResponse:
        return self._run("update_key", "Key updated successfully", webhook_url, confirm)

    def approve_imports(self, elements: list[str], confirm: bool = False) -> ETLResponse:
        """Posts the chosen fetched elements (none: nothing posted), then approve_imports is success (the job's end)."""
        elements = list(dict.fromkeys(elements))
        if missing := not_fetched(elements):  # before the gate: a refusal writes nothing
            raise PipelineBlockedError(f"Not fetched in this pass: {', '.join(missing)}. Launch its Pivot import again first")
        message = f"Imports approved, posted: {', '.join(elements) or 'nothing'}"
        return self._run("approve_imports", message, None, confirm, {"elements": elements})
