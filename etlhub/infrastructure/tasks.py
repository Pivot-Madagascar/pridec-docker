import logging
import traceback
from datetime import datetime

from etlhub.core.celery_app import celery_app
from etlhub.domain.exceptions import ETLException
from etlhub.application.use_cases.etl_use_cases import ETL_JOBS, notify_webhook, run_etl_job
from etlhub.infrastructure.forecast_runner import run_rscript
from etlhub.infrastructure.job_store import JobStore
from etlhub.infrastructure.checkpoint_store import get_checkpoint_store
from etlhub.infrastructure import etl_events

logger = logging.getLogger(__name__)


def _update_task_status(job_store: JobStore, job_id: str, status: str, message: str = None):
    task_status = job_store.get(job_id) or {"job_id": job_id}
    task_status.setdefault("started", datetime.now().isoformat())  # set when the worker starts, not at launch
    task_status["status"] = status
    if message:
        task_status["message"] = message
    job_store.set(job_id, task_status)
    if status in ("success", "error"):
        try:
            get_checkpoint_store().finish(job_id, status)
        except Exception:  # sqlite3, or Redis in test mode: the job's own status must not change
            # The lock stays taken until DELETE /pipeline/lock frees it.
            logger.exception("Could not record the end of %s in the pipeline checkpoints", job_id)
    try:
        etl_events.publish_status(job_id, status, message)
    except Exception:
        pass


def _run_task(job_id: str, task_name: str, run_fn, webhook_url: str | None = None):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", f"Starting {task_name}")
    try:
        run_fn(job_store=job_store, job_id=job_id)
        _update_task_status(job_store, job_id, "success", f"{task_name} completed")
        notify_webhook(webhook_url, job_id, "success", f"{task_name} completed")
    except Exception as e:
        tb = traceback.format_exc()
        job_store.append_logs(job_id, tb)  # after the job's own output (a forecast's R logs), not instead of it
        try:
            etl_events.publish_log(job_id, "ERROR", tb)
        except Exception:
            pass
        _update_task_status(job_store, job_id, "error", str(e))
        notify_webhook(webhook_url, job_id, "error", str(e))
        raise


@celery_app.task
def task_etl(task_type: str, job_id: str, webhook_url: str | None = None, **kwargs):
    """Every ETL_JOBS entry; kwargs go to the job function (validate_inputs paths)."""
    _run_task(job_id, ETL_JOBS[task_type][1],
              lambda job_store, job_id: run_etl_job(task_type, job_store, job_id, etl_events, **kwargs), webhook_url)


def _forecast(job_store, job_id: str, params: dict) -> None:
    # run_rscript saves the job record and the logs; the status it returns decides success.
    result = run_rscript(job_id, params, job_store)
    if result.get("status") != "success":
        raise ETLException(result.get("message") or "Forecast container failed")


@celery_app.task
def task_forecast(job_id: str, params: dict, webhook_url: str | None = None):
    _run_task(job_id, "forecast pipeline", lambda job_store, job_id: _forecast(job_store, job_id, params), webhook_url)


class CeleryTaskLauncher:
    def launch(self, task_type: str, job_id: str, webhook_url: str | None = None, confirm: bool = False,
               carry_over: dict[str, dict] | None = None, **kwargs) -> None:
        if task_type != "forecast" and task_type not in ETL_JOBS:
            raise ValueError(f"Unknown task type: {task_type}")
        gate = get_checkpoint_store()
        gate.start(task_type, job_id, confirm, carry_over)  # PipelineBlockedError -> 409, nothing queued
        # Known from the 202 on, before a worker picks it up: the log WebSocket and the
        # tracking page can follow it (an unknown job gets 4004).
        JobStore().set(job_id, {"job_id": job_id, "status": "pending", "message": "Queued"})
        try:
            if task_type == "forecast":
                task_forecast.delay(job_id, webhook_url=webhook_url, **kwargs)
            else:
                task_etl.delay(task_type, job_id, webhook_url=webhook_url, **kwargs)
        except Exception:
            gate.finish(job_id, "error")
            raise
