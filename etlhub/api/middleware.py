import uuid
import threading
import time
from contextlib import contextmanager
from urllib.parse import urlparse

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from etlhub.infrastructure.request_tracker import get_request_tracker
from etlhub.core.config import get_settings


def _should_track_request(url: str) -> bool:
    settings = get_settings()
    if not settings.tracked_endpoints:
        return True
    tracked = [e.strip() for e in settings.tracked_endpoints.split(",") if e.strip()]
    try:
        path = urlparse(url).path
        if path.startswith("/api/tracking"):
            return False
        return any(path.startswith(ep) for ep in tracked)
    except Exception:
        return True


def setup_cors(app):
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_tracker_local = threading.local()


@contextmanager
def track_service(service: str, method: str, url: str):
    start = time.perf_counter()
    entry = {"service": service, "method": method, "url": url}
    if not hasattr(_tracker_local, "calls"):
        _tracker_local.calls = []
    _tracker_local.calls.append(entry)
    _tracker_local.stack = getattr(_tracker_local, "stack", []) + [entry]
    try:
        yield entry
    except Exception as exc:
        entry["error"] = str(exc)
        raise
    finally:
        entry["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        if hasattr(_tracker_local, "stack") and _tracker_local.stack:
            _tracker_local.stack.pop()


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        _tracker_local.calls = []
        _tracker_local.stack = []
        _tracker_local.request_id = request_id

        request.state.request_id = request_id

        response: Response = await call_next(request)

        if _should_track_request(str(request.url)):
            duration = round((time.perf_counter() - start) * 1000, 2)
            log = {
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "duration_ms": duration,
                "client_host": request.client.host if request.client else None,
                "services": _tracker_local.calls,
                "error": None,
            }
            get_request_tracker().save(log)
        _tracker_local.calls = []
        _tracker_local.stack = []
        response.headers["X-Request-ID"] = request_id
        return response
