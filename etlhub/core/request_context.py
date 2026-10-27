from contextvars import ContextVar

# One dict per HTTP request, set by RequestTrackingMiddleware. A dict, not plain values: the endpoint runs in a copy of
# the context, so only mutations of this shared object reach the middleware back. None outside a request (Celery worker).
# Keys: request_id; actor (get_current_user); pipeline (the gate journaled or refused it: always tracked);
# journal (a production journal event refers to it: kept out of the request_log purge); reason, code (409 refusals).
request_context: ContextVar[dict | None] = ContextVar("request_context", default=None)
