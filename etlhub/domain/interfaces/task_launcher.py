from typing import Protocol

class TaskLauncher(Protocol):
    def launch(self, task_type: str, job_id: str, webhook_url: str | None = None, confirm: bool = False,
               **kwargs) -> None: ...