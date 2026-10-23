"""What RequestTrackingMiddleware records."""
import uuid

import pytest
from fastapi.testclient import TestClient

from etlhub.core.config import get_settings
from etlhub.infrastructure import request_tracker


class Recorder:
    def __init__(self):
        self.logs = []

    def save(self, log):
        self.logs.append(log)

    def list_recent(self, limit=50, endpoint=None):  # GET /api/tracking/requests reads the same tracker
        return []


@pytest.fixture
def recorded(monkeypatch, use_instance):
    recorder = Recorder()
    use_instance(monkeypatch, request_tracker.get_request_tracker, request_tracker, "RequestTracker", recorder)
    monkeypatch.setattr(get_settings(), "tracked_endpoints", "")
    return recorder.logs


@pytest.fixture
def crash_route(app):
    @app.get("/__test_crash")
    def crash():
        raise RuntimeError("boom")

    yield
    app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/__test_crash"]


def test_unhandled_error_is_recorded_as_500_with_the_error(app, recorded, crash_route):
    response = TestClient(app, raise_server_exceptions=False).get("/__test_crash")

    assert response.status_code == 500
    assert recorded[-1]["status_code"] == 500
    assert recorded[-1]["error"] == "RuntimeError: boom"


def test_tracking_routes_are_never_recorded_even_without_filter(app, recorded):
    TestClient(app).get("/api/tracking/requests")

    assert recorded == []


def test_tracked_endpoints_filter_by_path_prefix(app, recorded, monkeypatch):
    monkeypatch.setattr(get_settings(), "tracked_endpoints", "/input")
    client = TestClient(app)

    client.get("/docs")
    client.get("/input/files")

    assert [log["url"].split("testserver")[1] for log in recorded] == ["/input/files"]


def test_client_request_id_is_kept_only_if_it_is_a_uuid(app, recorded):
    client = TestClient(app)
    good = str(uuid.uuid4())

    client.get("/docs", headers={"X-Request-ID": good})
    response = client.get("/docs", headers={"X-Request-ID": "../other-request"})

    assert recorded[0]["request_id"] == good
    assert recorded[1]["request_id"] != "../other-request"
    assert uuid.UUID(recorded[1]["request_id"])
    assert response.headers["X-Request-ID"] == recorded[1]["request_id"]
    assert "services" not in recorded[0]
    assert recorded[0]["timestamp"].endswith("+00:00")


def test_job_id_of_a_launch_is_recorded_and_the_body_is_intact(override_dependencies, recorded):
    response = TestClient(override_dependencies).post("/import_gee")

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert job_id.startswith("import_gee_")
    assert recorded[-1]["job_id"] == job_id


def test_non_json_or_job_less_responses_have_no_job_id(app, recorded):
    TestClient(app).get("/docs")         # HTML page
    TestClient(app).get("/input/files")  # JSON without job_id

    assert [log["job_id"] for log in recorded] == [None, None]


def test_a_pipeline_refusal_is_recorded_with_its_reason_even_outside_tracked_endpoints(app, recorded, monkeypatch):
    monkeypatch.setattr(get_settings(), "tracked_endpoints", "/nothing")

    response = TestClient(app).post("/pipeline/runs", json={"source": "COM", "disease": "Malaria"})

    assert response.status_code == 409
    assert recorded[-1]["reason"] == response.json()["message"]
    assert "code" not in recorded[-1] and "journal" not in recorded[-1]


def test_a_confirmation_request_is_recorded_with_its_code(app, recorded, checkpoint_store):
    checkpoint_store.start("import_gee", "done")
    checkpoint_store.finish("done", "success")

    response = TestClient(app).post("/import_gee")  # refused by the gate before anything is queued

    assert response.status_code == 409
    assert recorded[-1]["code"] == "confirmation_required"


def test_a_journaled_request_is_recorded_and_flagged_for_the_journal(app, recorded, monkeypatch):
    monkeypatch.setattr(get_settings(), "tracked_endpoints", "/nothing")

    TestClient(app).put("/pipeline/mode", json={"test_mode": True})

    assert recorded[-1]["journal"] is True
