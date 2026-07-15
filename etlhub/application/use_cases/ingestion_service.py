import uuid

from etlhub.domain.interfaces.task_launcher import TaskLauncher


class IngestionService:
    def __init__(self, task_launcher: TaskLauncher):
        self._task_launcher = task_launcher

    def import_gee(self, webhook_url: str | None = None) -> str:
        job_id = f"import_gee_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("import_gee", job_id, webhook_url=webhook_url)
        return job_id

    def import_pivot_com(self, webhook_url: str | None = None) -> str:
        job_id = f"import_pivot_com_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("import_pivot_com", job_id, webhook_url=webhook_url)
        return job_id

    def import_pivot_csb(self, webhook_url: str | None = None) -> str:
        job_id = f"import_pivot_csb_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("import_pivot_csb", job_id, webhook_url=webhook_url)
        return job_id

    def fetch_climate(self, webhook_url: str | None = None) -> str:
        job_id = f"fetch_climate_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("fetch_climate", job_id, webhook_url=webhook_url)
        return job_id

    def fetch_disease(self, webhook_url: str | None = None) -> str:
        job_id = f"fetch_disease_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("fetch_disease", job_id, webhook_url=webhook_url)
        return job_id

    def fetch_geojson(self, webhook_url: str | None = None) -> str:
        job_id = f"fetch_geojson_{uuid.uuid4().hex[:8]}"
        self._task_launcher.launch("fetch_geojson", job_id, webhook_url=webhook_url)
        return job_id