import json
import traceback
import urllib.request
import urllib.error
from datetime import datetime
from celery import current_task

from etlhub.core.celery_app import celery_app
from etlhub.application.use_cases.etl_use_cases import (
    run_import_gee,
    run_import_pivot_com,
    run_import_pivot_csb,
    run_fetch_climate,
    run_fetch_disease,
    run_fetch_geojson,
    run_build_analytics,
    run_calc_csb_alerts,
)
from etlhub.application.use_cases.validation_use_cases import run_validate_inputs
from etlhub.infrastructure.forecast_runner import run_rscript
from etlhub.infrastructure.job_store import JobStore


def _send_webhook(webhook_url: str, job_id: str, status: str, message: str, logs_url: str | None = None):
    try:
        payload = json.dumps({
            "job_id": job_id,
            "status": status,
            "message": message,
            "logs_url": logs_url,
        }).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _update_task_status(job_store: JobStore, job_id: str, status: str, message: str = None, logs: str = None):
    task_status = {
        "status": status,
        "started": current_task.request.time_started if hasattr(current_task.request, 'time_started') else datetime.now().isoformat(),
        "job_id": job_id,
    }
    if message:
        task_status["message"] = message
    if logs:
        task_status["logs"] = logs
    job_store.set(job_id, task_status)
    try:
        from etlhub.api.etl_events import get_etl_event_manager
        get_etl_event_manager().publish_status(job_id, status, message)
    except Exception:
        pass


def _run_task(self, job_id: str, task_name: str, run_fn, webhook_url: str | None = None):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", f"Starting {task_name}")
    try:
        run_fn(job_store=job_store, job_id=job_id)
        _update_task_status(job_store, job_id, "success", f"{task_name} completed")
        if webhook_url:
            _send_webhook(
                webhook_url,
                job_id=job_id,
                status="success",
                message=f"{task_name} completed",
                logs_url=f"/api/tracking/etl-logs/{job_id}",
            )
    except Exception as e:
        tb = traceback.format_exc()
        try:
            job_store.save_logs(job_id, tb)
        except Exception:
            pass
        try:
            from etlhub.api.etl_events import get_etl_event_manager
            get_etl_event_manager().publish_log(job_id, "ERROR", tb)
        except Exception:
            pass
        _update_task_status(job_store, job_id, "error", str(e))
        if webhook_url:
            _send_webhook(
                webhook_url,
                job_id=job_id,
                status="error",
                message=str(e),
                logs_url=f"/api/tracking/etl-logs/{job_id}",
            )
        raise


@celery_app.task(bind=True)
def task_import_gee(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "GEE import", run_import_gee, webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_import_pivot_com(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "Pivot COM import", run_import_pivot_com, webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_import_pivot_csb(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "Pivot CSB import", run_import_pivot_csb, webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_fetch_climate(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "climate data fetch", run_fetch_climate, webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_fetch_disease(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "disease data fetch", run_fetch_disease, webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_fetch_geojson(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "GeoJSON fetch", run_fetch_geojson, webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_build_analytics(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "analytics build", run_build_analytics, webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_calc_csb_alerts(self, job_id: str, webhook_url: str | None = None):
    _run_task(self, job_id, "CSB alerts calculation", run_calc_csb_alerts, webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_validate_inputs(self, job_id: str, webhook_url: str | None = None, **kwargs):
    _run_task(self, job_id, "validate inputs", lambda job_store, job_id: run_validate_inputs(
        job_store=job_store, job_id=job_id, **kwargs
    ), webhook_url=webhook_url)


@celery_app.task(bind=True)
def task_forecast(self, job_id: str, params: dict, webhook_url: str | None = None):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting forecast pipeline")
    try:
        run_rscript(job_id, params, job_store)
        _update_task_status(job_store, job_id, "success", "Forecast pipeline completed")
        if webhook_url:
            _send_webhook(
                webhook_url,
                job_id=job_id,
                status="success",
                message="Forecast pipeline completed",
                logs_url=f"/api/tracking/etl-logs/{job_id}",
            )
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        if webhook_url:
            _send_webhook(
                webhook_url,
                job_id=job_id,
                status="error",
                message=str(e),
                logs_url=f"/api/tracking/etl-logs/{job_id}",
            )
        raise