"""FetchedImports in Redis: the Pivot imports' last fetch, kept across logouts and forecast runs (opening a run empties
input/, where they were files until 2026-11-23)."""
import json

from etlhub.core.job_context import current_test_mode
from etlhub.infrastructure.checkpoint_store import get_checkpoint_store
from etlhub.infrastructure.redis_client import get_redis

KEY = "pivot_fetched:{mode}:{pass_id}:{task}"


class RedisFetchedImports:
    """One key per import, pass and mode, never expiring: a resumed pass finds its fetch again.

    ponytail: the keys of abandoned or old passes stay (a few hundred kB each); delete them with their pass if Redis grows.
    """

    def _key(self, task: str) -> str:
        p = get_checkpoint_store().progress()["pass"]  # the pass shown: during a job, its active one
        mode = "test" if current_test_mode() else "production"
        return KEY.format(mode=mode, pass_id=p["id"] if p else "-", task=task)

    def save(self, task: str, items: list[dict]) -> None:
        get_redis().set(self._key(task), json.dumps(items, default=str))

    def load(self, task: str) -> list[dict]:
        raw = get_redis().get(self._key(task))
        return json.loads(raw) if raw else []
