"""Guard: HTTP handlers are plain `def` (FastAPI's threadpool), so their SQLite, Redis and file work never blocks the
event loop, and every request and log WebSocket with it (known-issues §3, 2026-11-27)."""
import inspect
from types import SimpleNamespace

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from etlhub.api.routers import forecast_report_router

# Handlers that do no blocking work: they may stay async.
ASYNC_OK = {"/"}  # main.root: a redirect


def test_http_handlers_run_off_the_event_loop(app):
    async_routes = [r.path for r in app.routes if isinstance(r, APIRoute)
                    and inspect.iscoroutinefunction(r.endpoint) and r.path not in ASYNC_OK]
    assert async_routes == []


def test_the_session_s_mode_reaches_a_def_handler(anon_app, monkeypatch, tmp_path):
    """The async get_current_user sets the mode ContextVar; the def handler runs in a thread with a copy of it."""
    from etlhub.api.auth import dhis2_auth

    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    (tmp_path / "test" / "output").mkdir(parents=True)
    (tmp_path / "test" / "output" / "forecast_report.html").write_text("<p>test</p>")

    for test_mode, status in ((True, 200), (False, 404)):
        monkeypatch.setattr(dhis2_auth, "session_from_cookies",
                            lambda cookies, t=test_mode: {"user": {"username": "jdoe"}, "test_mode": t})
        assert TestClient(anon_app).get("/output/forecast_report.html").status_code == status
