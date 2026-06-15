from functools import lru_cache
from etlhub.infrastructure.job_store import JobStore


@lru_cache
def get_job_store() -> JobStore:
    return JobStore()
