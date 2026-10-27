from typing import Protocol

class TaskLauncher(Protocol):
    # carry_over: the imports' parameters, passed to PipelineGate.start.
    def launch(self, task_type: str, job_id: str, webhook_url: str | None = None, confirm: bool = False,
               carry_over: dict[str, dict] | None = None, **kwargs) -> None: ...