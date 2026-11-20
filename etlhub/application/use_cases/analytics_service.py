import uuid

from etlhub.application.use_cases.etl_use_cases import notify_webhook, run_etl_job
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.interfaces.event_publisher import EventPublisher
from etlhub.domain.exceptions import ETLException, PipelineBlockedError
from etlhub.domain.schemas import ETLResponse

# Inline jobs running in this API process: whether the holder of the pipeline lock is still alive (DELETE /pipeline/lock).
# ponytail: one set per process, right with a single API process (run_server.py); several would need a shared registry.
RUNNING_INLINE: set[str] = set()


class AnalyticsService:
    """post_forecast and update_key: run synchronously, inside the pipeline gate."""

    def __init__(self, job_repo: JobRepository, gate: PipelineGate, events: EventPublisher):
        self._job_repo = job_repo
        self._gate = gate
        self._events = events

    def _run(self, task_type: str, message: str, webhook_url: str | None, confirm: bool,
             dry_run: bool | None) -> ETLResponse:
        job_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        fixed = (self._gate.pass_config() or {}).get("dry_run")  # the pass's, fixed when it started (pass-config.md)
        if dry_run is None:
            dry_run = self._gate.default_dry_run() if fixed is None else fixed
        if task_type == "update_key" and dry_run:
            # Before the gate: a refusal writes nothing.
            raise PipelineBlockedError(
                "update_key cannot run in dry run: pivot_dhis_tools ignores its dryRun and writes the PRIDE-C key to "
                "DHIS2 anyway. " + ("This pass runs in dry run, fixed when it started: only a pass started without dry "
                                    "run can update the key." if fixed else "Launch it with dry_run=false."))
        with self._gate.run(task_type, job_id, confirm, dry_run) as dry_run:  # PipelineBlockedError propagates as is
            RUNNING_INLINE.add(job_id)
            try:
                run_etl_job(task_type, self._job_repo, job_id, self._events, dry_run=dry_run)
            except ETLException as e:
                raise ETLException(f"{task_type} failed: {e}") from e
            finally:
                RUNNING_INLINE.discard(job_id)
        notify_webhook(webhook_url, job_id, "success", message)
        return ETLResponse(status="success", message=message, job_id=job_id, webhook_url=webhook_url)

    def post_forecast(self, webhook_url: str | None = None, confirm: bool = False,
                      dry_run: bool | None = None) -> ETLResponse:
        return self._run("post_forecast", "Forecast posted successfully", webhook_url, confirm, dry_run)

    def update_key(self, webhook_url: str | None = None, confirm: bool = False,
                   dry_run: bool | None = None) -> ETLResponse:
        return self._run("update_key", "Key updated successfully", webhook_url, confirm, dry_run)
