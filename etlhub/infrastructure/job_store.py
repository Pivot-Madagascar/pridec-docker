import json
import logging
import sys
from pathlib import Path
from etlhub.core.config import get_settings
from etlhub.infrastructure.redis_client import get_redis

# Not through the root handlers: during a job, etl/scripts/config.setup_logging() (basicConfig(force=True) under
# redirect_stderr) binds them to the job's _JobLogger, whose write() calls append_logs. A failure logged there would
# loop back into append_logs until RecursionError. This logger writes to the real stderr only.
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.__stderr__))
logger.propagate = False

# job:<id> and etl_logs:<id> in Redis: the tracking page and the log WebSocket read them. logs/<id>.log keeps the logs
# for good (logs/<id>.json the status, forecasts only). ponytail: no maxmemory on the redis service, so 30 days of
# job logs stay in memory; cap it if Redis grows.
JOB_TTL_SECONDS = 30 * 24 * 3600


class JobStore:
    """Job records and log history. A failure is logged and never raised: storing must not fail the job itself."""

    def get(self, job_id: str) -> dict | None:
        try:
            redis_client = get_redis()
            data = redis_client.get(f"job:{job_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("JobStore.get(%s) failed: %s", job_id, e)
        return None

    def set(self, job_id: str, data: dict) -> None:
        try:
            redis_client = get_redis()
            redis_client.setex(
                f"job:{job_id}",
                JOB_TTL_SECONDS,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning("JobStore.set(%s) failed: %s", job_id, e)

    def append_logs(self, job_id: str, text: str) -> None:
        # Called from _JobLogger.write, which stands for sys.stdout/stderr during a job: see `logger` above.
        try:
            redis_client = get_redis()
            redis_client.append(f"etl_logs:{job_id}", text)
            redis_client.expire(f"etl_logs:{job_id}", JOB_TTL_SECONDS)
        except Exception as e:
            logger.warning("JobStore.append_logs(%s) to Redis failed: %s", job_id, e)
        try:
            logs_dir = Path(get_settings().logs_dir)
            logs_dir.mkdir(parents=True, exist_ok=True)
            with open(logs_dir / f"{job_id}.log", "a") as f:
                f.write(text)
        except Exception as e:
            logger.warning("JobStore.append_logs(%s) to file failed: %s", job_id, e)

    def get_logs(self, job_id: str) -> str | None:
        try:
            redis_client = get_redis()
            data = redis_client.get(f"etl_logs:{job_id}")
            if data:
                return data
        except Exception as e:
            logger.warning("JobStore.get_logs(%s) from Redis failed, reading the file: %s", job_id, e)
        log_file = Path(get_settings().logs_dir) / f"{job_id}.log"
        if log_file.exists():
            return log_file.read_text()
        return None

    def load_from_file(self, job_id: str, logs_dir: str) -> dict | None:
        status_file = Path(logs_dir) / f"{job_id}.json"
        if status_file.exists():
            return json.loads(status_file.read_text())
        return None
