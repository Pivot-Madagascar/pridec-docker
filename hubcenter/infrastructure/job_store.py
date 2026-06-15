import json
from pathlib import Path


class JobStore:
    _jobs: dict = {}

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def set(self, job_id: str, data: dict) -> None:
        self._jobs[job_id] = data

    def load_from_file(self, job_id: str, logs_dir: str) -> dict | None:
        status_file = Path(logs_dir) / f"{job_id}.json"
        if status_file.exists():
            return json.loads(status_file.read_text())
        return None
