from typing import Protocol, Any, Optional

class JobRepository(Protocol):
    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        ...

    def set(self, job_id: str, data: dict[str, Any]) -> None:
        ...

    def append_logs(self, job_id: str, text: str) -> None:
        ...

    def get_logs(self, job_id: str) -> Optional[str]:
        ...

    def load_from_file(self, job_id: str, logs_dir: str) -> Optional[dict[str, Any]]:
        ...