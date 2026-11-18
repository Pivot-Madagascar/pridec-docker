from typing import Protocol

class TaskLauncher(Protocol):
    # carry_over: the imports' parameters, passed to PipelineGate.start. dry_run: the launch's choice (None = default).
    def launch(self, task_type: str, job_id: str, webhook_url: str | None = None, confirm: bool = False,
               carry_over: dict[str, dict] | None = None, dry_run: bool | None = None, **kwargs) -> None: ...

    # True: still running (a worker has it, or this API process runs it inline). False: not running anywhere.
    # None: unknown (no worker answered). Liveness only, never elapsed time: jobs have no timeout, by decision.
    def is_active(self, job_id: str) -> bool | None: ...