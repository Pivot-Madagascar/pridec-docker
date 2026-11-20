import logging
import traceback
from datetime import datetime

from etlhub.core.celery_app import celery_app
from etlhub.core.job_context import current_test_mode, job_pass_config, pipeline_test_mode
from etlhub.domain.exceptions import ETLException
from etlhub.application.use_cases.analytics_service import RUNNING_INLINE
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
    except Exception as e:
        logger.warning("Could not publish the %s status of %s: %s", status, job_id, e)


def _run_task(job_id: str, task_name: str, run_fn, webhook_url: str | None = None, test_mode: bool | None = None,
              pass_config: dict | None = None):
    """test_mode: the mode of the user who launched the job (None: a task queued before it was sent, test).
    pass_config: the fixed configuration of its pass, read at its launch (None: queued before 2026-11-20)."""
    token = pipeline_test_mode.set(test_mode)  # the job's store, folders and end, in the launcher's mode
    config_token = job_pass_config.set(pass_config)
    try:
        _run(job_id, task_name, run_fn, webhook_url)
    finally:
        job_pass_config.reset(config_token)
        pipeline_test_mode.reset(token)


def _run(job_id: str, task_name: str, run_fn, webhook_url: str | None) -> None:
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
        except Exception as pub_error:
            logger.warning("Could not publish the error log of %s: %s", job_id, pub_error)
        _update_task_status(job_store, job_id, "error", str(e))
        notify_webhook(webhook_url, job_id, "error", str(e))
        raise


@celery_app.task
def task_etl(task_type: str, job_id: str, webhook_url: str | None = None, test_mode: bool | None = None,
             pass_config: dict | None = None, **kwargs):
    """Every ETL_JOBS entry; kwargs go to the job function (validate_inputs paths)."""
    _run_task(job_id, ETL_JOBS[task_type][1],
              lambda job_store, job_id: run_etl_job(task_type, job_store, job_id, etl_events, **kwargs), webhook_url,
              test_mode, pass_config)


def _forecast(job_store, job_id: str, params: dict) -> None:
    # run_rscript saves the job record and the logs; the status it returns decides success.
    result = run_rscript(job_id, params, job_store)
    if result.get("status") != "success":
        raise ETLException(result.get("message") or "Forecast container failed")


@celery_app.task
def task_forecast(job_id: str, params: dict, webhook_url: str | None = None, test_mode: bool | None = None,
                  pass_config: dict | None = None):
    _run_task(job_id, "forecast pipeline", lambda job_store, job_id: _forecast(job_store, job_id, params), webhook_url,
              test_mode, pass_config)


class CeleryTaskLauncher:
    def launch(self, task_type: str, job_id: str, webhook_url: str | None = None, confirm: bool = False,
               carry_over: dict[str, dict] | None = None, dry_run: bool | None = None, **kwargs) -> None:
        if task_type != "forecast" and task_type not in ETL_JOBS:
            raise ValueError(f"Unknown task type: {task_type}")
        gate = get_checkpoint_store()
        dry_run = gate.start(task_type, job_id, confirm, carry_over, dry_run)  # PipelineBlockedError -> 409, nothing queued
        # Known from the 202 on, before a worker picks it up: the log WebSocket and the
        # tracking page can follow it (an unknown job gets 4004).
        JobStore().set(job_id, {"job_id": job_id, "status": "pending", "message": "Queued"})
        # The user's mode, and the configuration of the job's pass: the job reads its own pass's, never the active one
        # when it starts (the lock forbids a pause meanwhile; this survives a manual unlock).
        mode = {"test_mode": current_test_mode(), "pass_config": gate.pass_config()}
        try:
            # task_id=job_id: is_active finds the job among the workers' tasks.
            if task_type == "forecast":
                task_forecast.apply_async((job_id,), {"webhook_url": webhook_url, **mode, **kwargs}, task_id=job_id)
            else:
                task_etl.apply_async((task_type, job_id),
                                     {"webhook_url": webhook_url, "dry_run": dry_run, **mode, **kwargs}, task_id=job_id)
        except Exception:
            gate.finish(job_id, "error")
            raise

    def is_active(self, job_id: str) -> bool | None:
        if job_id in RUNNING_INLINE:
            return True
        # Running or prefetched by a worker. A worker restarted after a kill prefetches the queued task again: active.
        # The control broadcast waits celery's default 1 s for the workers' replies: it limits the question, not the job.
        try:
            replies = celery_app.control.inspect().query_task(job_id)  # {worker: {task_id: [state, info]}}, or None
        except Exception as e:  # broker unreachable: unknown, the user decides
            logger.warning("Could not ask the workers about %s: %s", job_id, e)
            return None
        if not replies:
            return None
        return any(tasks.get(job_id, ("ready",))[0] in ("active", "reserved") for tasks in replies.values())
