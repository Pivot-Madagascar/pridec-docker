"""Guard: every route needs a session, except an explicit public list.

A new route added without the session dependency makes this test fail.
"""
import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from etlhub.api.auth.dhis2_auth import WS_NOT_AUTHENTICATED
from etlhub.api.websockets import etl_logs

# FastAPI's own /docs, /redoc and /openapi.json are not APIRoute: they stay public for now.
PUBLIC = {
    ("GET", "/"),
    ("POST", "/auth/login"),
    ("POST", "/auth/logout"),
    ("GET", "/auth/dhis2-urls"),
}


def _routes(app):
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in sorted(route.methods - {"HEAD"}):
                yield method, route.path


def test_every_route_requires_a_session(anon_app):
    client = TestClient(anon_app)
    open_routes = []
    for method, path in _routes(anon_app):
        if (method, path) in PUBLIC:
            continue
        status = client.request(method, re.sub(r"\{[^}]+\}", "x", path)).status_code
        if status != 401:
            open_routes.append((method, path, status))

    assert open_routes == []


def test_the_guard_actually_sees_the_routes(anon_app):
    routes = set(_routes(anon_app))
    assert ("POST", "/import_gee") in routes
    assert ("DELETE", "/pipeline/lock") in routes
    assert len(routes) >= 25


def test_log_websocket_without_session_is_closed_with_4401(anon_app):
    with TestClient(anon_app).websocket_connect("/api/tracking/etl-logs/job_1") as ws:
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == WS_NOT_AUTHENTICATED


def test_log_websocket_from_another_origin_is_refused(anon_app):
    with pytest.raises(WebSocketDisconnect):
        with TestClient(anon_app).websocket_connect(
            "/api/tracking/etl-logs/job_1", headers={"Origin": "http://localhost:8082"}
        ) as ws:
            ws.receive_json()


def test_log_websocket_with_session_goes_past_the_check(app, fake_ws_redis):
    with TestClient(app).websocket_connect("/api/tracking/etl-logs/job_1") as ws:
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 4004  # unknown job, after the session check


def test_openapi_documents_every_operation_and_its_session(anon_app):
    """Each operation has a description; the session cookie and its 401 are declared exactly where it is required."""
    operations = [(m.upper(), path, op) for path, ops in anon_app.openapi()["paths"].items() for m, op in ops.items()]
    assert [(m, p) for m, p, op in operations if not op.get("description")] == []
    assert {(m, p) for m, p, op in operations if "security" not in op} == PUBLIC - {("GET", "/")}
    assert [(m, p) for m, p, op in operations if "security" in op and "401" not in op["responses"]] == []
