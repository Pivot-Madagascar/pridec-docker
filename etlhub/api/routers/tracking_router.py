from fastapi import APIRouter, WebSocket, Depends, Query

from etlhub.api.routers import error_doc
from etlhub.application.use_cases.tracking_service import TrackingService
from etlhub.api.websockets.etl_logs import handle_etl_logs_ws
from etlhub.core.dependencies import get_event_subscriber, get_pipeline_gate, get_tracking_service
from etlhub.domain.interfaces.event_subscriber import EventSubscriber
from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.schemas.tracking import RequestLog, ETLLog

router = APIRouter(prefix="/api/tracking", tags=["Tracking"])

# JobNotFoundError handler (main.py): same body for an unknown request and an unknown job.
_NOT_FOUND = {404: error_doc("Unknown id, or expired from Redis and absent from logs/", {"message": "Job not found"})}


@router.get(
    "/requests",
    response_model=list[RequestLog],
    summary="Recent HTTP requests",
    description=(
        "Requests recorded by RequestTrackingMiddleware, newest first, in the current mode (TEST_MODE) only: a request "
        "recorded in the other mode, or before the mode was recorded, is never listed."
    ),
)
def list_requests(
    limit: int = Query(50, description="Maximum number of entries"),
    endpoint: str | None = Query(None, description="Keep only requests whose URL contains this text"),
    service: TrackingService = Depends(get_tracking_service),
):
    return service.list_requests(limit, endpoint)


@router.get(
    "/requests/{request_id}",
    response_model=RequestLog,
    summary="One recorded HTTP request",
    description=(
        "request_id is the X-Request-ID header the request was sent with (or the one etlhub generated). "
        "A request of the other mode is not found (404)."
    ),
    responses=_NOT_FOUND,
)
def get_request(request_id: str, service: TrackingService = Depends(get_tracking_service)):
    return service.get_request(request_id)


@router.get(
    "/etl-logs/{job_id}",
    response_model=ETLLog,
    summary="Logs of a job",
    description=(
        "Log text of the job, plus its status and message while the job record exists in Redis (30 days). "
        "Only for a job the pipeline of the current mode launched: one of the other mode is not found (404, 4004). "
        "Live stream: WebSocket on the same path (not described by OpenAPI; messages etl_log_history, "
        "job_status_update, etl_log_entry, etl_log_complete; close code 4004 unknown job, 4401 no session)."
    ),
    responses=_NOT_FOUND,
)
def get_etl_logs(job_id: str, service: TrackingService = Depends(get_tracking_service)):
    return service.get_etl_logs(job_id)


@router.websocket("/etl-logs/{job_id}")
async def websocket_etl_logs(
    websocket: WebSocket, job_id: str,
    gate: PipelineGate = Depends(get_pipeline_gate), events: EventSubscriber = Depends(get_event_subscriber),
):
    await handle_etl_logs_ws(websocket, job_id, gate, events)