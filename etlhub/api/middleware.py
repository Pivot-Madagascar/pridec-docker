import json
import re
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response

from etlhub.infrastructure.request_tracker import get_request_tracker
from etlhub.core.config import get_settings
from etlhub.core.request_context import request_context


def _should_track_request(path: str) -> bool:
    # Reading the tracking must not fill the tracking: never record /api/tracking, filter or not.
    if path.startswith("/api/tracking"):
        return False
    tracked = [e.strip() for e in get_settings().tracked_endpoints.split(",") if e.strip()]
    return not tracked or any(path.startswith(ep) for ep in tracked)


def _request_id(header: str | None) -> str:
    """Client X-Request-ID only if it is a UUID: anything else could overwrite another entry."""
    try:
        return str(uuid.UUID(header))
    except (TypeError, ValueError):
        return str(uuid.uuid4())


def setup_cors(app):
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def is_allowed_origin(origin: str | None) -> bool:
    """True when there is no Origin (not a browser) or it is the etlui origin.

    The session cookie is SameSite=Strict, but every port of the same host (DHIS2 on
    :8082, for instance) counts as the same site, so the origin is checked too.
    Requests without Origin (curl, scripts) are left to the session check.
    """
    return not origin or origin.rstrip("/") == get_settings().frontend_url.rstrip("/")


async def check_origin(request: Request, call_next):
    """Refuse state-changing browser requests from another origin."""
    if request.method in _UNSAFE_METHODS and not is_allowed_origin(request.headers.get("origin")):
        return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})
    return await call_next(request)


# Frozen job_id format: <task_type>_<8 hex>.
_JOB_ID = re.compile(r"^[a-z_]+_[0-9a-f]{8}$")
_MAX_JOB_BODY = 64 * 1024


async def _with_job_id(response: Response) -> tuple[Response, str | None]:
    """Read `job_id` from a small JSON response (job launches, job status).

    The body can only be read once, so the response is rebuilt from it. Large or
    non-JSON responses (previews, the HTML report) are left untouched.
    """
    length = response.headers.get("content-length")
    if "application/json" not in response.headers.get("content-type", "") or not length or int(length) > _MAX_JOB_BODY:
        return response, None
    body = b"".join([chunk async for chunk in response.body_iterator])
    rebuilt = Response(content=body, status_code=response.status_code, headers=dict(response.headers))
    try:
        job_id = json.loads(body).get("job_id")
    except (ValueError, AttributeError):
        job_id = None
    return rebuilt, job_id if isinstance(job_id, str) and _JOB_ID.match(job_id) else None


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = _request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        context = {"request_id": request_id}
        token = request_context.set(context)

        status_code, error, job_id = 500, None, None
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            if _tracked(request.url.path, context):
                response, job_id = await _with_job_id(response)
        except Exception as exc:
            # Unhandled errors are the requests most worth tracking: record them, then re-raise.
            error = f"{type(exc).__name__}: {exc}"[:300]
            raise
        finally:
            request_context.reset(token)
            if _tracked(request.url.path, context):
                log = {
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "client_host": request.client.host if request.client else None,
                    "error": error,
                    "job_id": job_id,
                    # 409 reason and code, and the journal flag the purge reads (core/request_context.py).
                    **{k: context[k] for k in ("reason", "code", "journal") if k in context},
                }
                # SQLite write off the event loop.
                await run_in_threadpool(get_request_tracker().save, log)

        response.headers["X-Request-ID"] = request_id
        return response


def _tracked(path: str, context: dict) -> bool:
    """TRACKED_ENDPOINTS, plus every request the pipeline gate journaled or refused: the journal links to them."""
    return _should_track_request(path) or context.get("pipeline", False)
