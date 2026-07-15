from typing import Protocol, runtime_checkable, Any

@runtime_checkable
class TaskLauncher(Protocol):
    def launch(self, task_type: str, job_id: str, webhook_url: str | None = None, **kwargs) -> None: ...