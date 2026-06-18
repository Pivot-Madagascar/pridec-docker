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
from etlhub.infrastructure.forecast_runner import run_rscript
from etlhub.infrastructure.job_store import JobStore


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


@celery_app.task(bind=True)
def task_import_gee(self, job_id: str):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting GEE import")
    try:
        run_import_gee()
        _update_task_status(job_store, job_id, "success", "GEE import completed")
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise


@celery_app.task(bind=True)
def task_import_pivot_com(self, job_id: str):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting Pivot COM import")
    try:
        run_import_pivot_com()
        _update_task_status(job_store, job_id, "success", "Pivot COM import completed")
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise


@celery_app.task(bind=True)
def task_import_pivot_csb(self, job_id: str):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting Pivot CSB import")
    try:
        run_import_pivot_csb()
        _update_task_status(job_store, job_id, "success", "Pivot CSB import completed")
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise


@celery_app.task(bind=True)
def task_fetch_climate(self, job_id: str):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting climate data fetch")
    try:
        run_fetch_climate()
        _update_task_status(job_store, job_id, "success", "Climate data fetch completed")
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise


@celery_app.task(bind=True)
def task_fetch_disease(self, job_id: str):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting disease data fetch")
    try:
        run_fetch_disease()
        _update_task_status(job_store, job_id, "success", "Disease data fetch completed")
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise


@celery_app.task(bind=True)
def task_fetch_geojson(self, job_id: str):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting GeoJSON fetch")
    try:
        run_fetch_geojson()
        _update_task_status(job_store, job_id, "success", "GeoJSON fetch completed")
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise


@celery_app.task(bind=True)
def task_build_analytics(self, job_id: str):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting analytics build")
    try:
        run_build_analytics()
        _update_task_status(job_store, job_id, "success", "Analytics build completed")
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise


@celery_app.task(bind=True)
def task_calc_csb_alerts(self, job_id: str):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting CSB alerts calculation")
    try:
        run_calc_csb_alerts()
        _update_task_status(job_store, job_id, "success", "CSB alerts calculation completed")
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise


@celery_app.task(bind=True)
def task_forecast(self, job_id: str, params: dict):
    job_store = JobStore()
    _update_task_status(job_store, job_id, "running", "Starting forecast pipeline")
    try:
        run_rscript(job_id, params, job_store)
    except Exception as e:
        _update_task_status(job_store, job_id, "error", str(e))
        raise