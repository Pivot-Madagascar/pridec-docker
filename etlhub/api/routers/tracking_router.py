from fastapi import APIRouter, HTTPException, WebSocket

from etlhub.infrastructure.request_tracker import get_request_tracker
from etlhub.infrastructure.job_store import JobStore
from etlhub.domain.schemas.tracking import RequestLog, ETLLog
from etlhub.api.websockets.etl_logs import handle_etl_logs_ws

router = APIRouter(prefix="/api/tracking", tags=["Tracking"])


@router.get("/requests", response_model=list[RequestLog])
def list_requests(limit: int = 50):
    tracker = get_request_tracker()
    return tracker.list_recent(limit=limit)


@router.get("/requests/{request_id}", response_model=RequestLog)
def get_request(request_id: str):
    tracker = get_request_tracker()
    log = tracker.get(request_id)
    if not log:
        raise HTTPException(status_code=404, detail="Request not found")
    return log


@router.get("/etl-logs/{job_id}", response_model=ETLLog)
def get_etl_logs(job_id: str):
    job_store = JobStore()
    logs = job_store.get_logs(job_id)
    if logs is None:
        raise HTTPException(status_code=404, detail="ETL logs not found for this job_id")
    return ETLLog(job_id=job_id, logs=logs)


@router.websocket("/etl-logs/{job_id}")
async def websocket_etl_logs(websocket: WebSocket, job_id: str):
    await handle_etl_logs_ws(websocket, job_id)
