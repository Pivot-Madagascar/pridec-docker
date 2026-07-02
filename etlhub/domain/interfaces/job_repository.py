from typing import Protocol, runtime_checkable, Any, Optional

@runtime_checkable
class JobRepository(Protocol):
    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        ...

    def set(self, job_id: str, data: dict[str, Any]) -> None:
        ...

    def save_logs(self, job_id: str, logs: str) -> None:
        ...

    def get_logs(self, job_id: str) -> Optional[str]:
        ...

    def load_from_file(self, job_id: str, logs_dir: str) -> Optional[dict[str, Any]]:
        ...