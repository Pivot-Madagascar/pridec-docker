from fastapi import APIRouter, WebSocket, Depends

from etlhub.application.use_cases.tracking_service import TrackingService
from etlhub.api.websockets.etl_logs import handle_etl_logs_ws
from etlhub.core.dependencies import get_tracking_service
from etlhub.domain.schemas.tracking import RequestLog, ETLLog

router = APIRouter(prefix="/api/tracking", tags=["Tracking"])


@router.get("/requests", response_model=list[RequestLog])
async def list_requests(limit: int = 50, service: TrackingService = Depends(get_tracking_service)):
    return service.list_requests(limit)


@router.get("/requests/{request_id}", response_model=RequestLog)
async def get_request(request_id: str, service: TrackingService = Depends(get_tracking_service)):
    return service.get_request(request_id)


@router.get("/etl-logs/{job_id}", response_model=ETLLog)
async def get_etl_logs(job_id: str, service: TrackingService = Depends(get_tracking_service)):
    return service.get_etl_logs(job_id)


@router.websocket("/etl-logs/{job_id}")
async def websocket_etl_logs(websocket: WebSocket, job_id: str):
    await handle_etl_logs_ws(websocket, job_id)