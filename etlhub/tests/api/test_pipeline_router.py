"""The pipeline gate seen from the API and from the Celery tasks (real gate, temporary db)."""
import pytest
from fastapi.testclient import TestClient

from etlhub.infrastructure import tasks
from tests.infrastructure.test_checkpoint_store import _import, _prepare
from tests.infrastructure.test_forecast_task import InMemoryJobStore


@pytest.fixture
def queue(monkeypatch):
    """Celery replaced: records the queued jobs."""
    InMemoryJobStore.records = {}
    monkeypatch.setattr(tasks, "JobStore", InMemoryJobStore)
    queued = []
    monkeypatch.setattr(tasks.task_etl, "delay", lambda task_type, *a, **k: queued.append((a, k)))
    return queued


@pytest.fixture
def upload_app(app, tmp_path):
    """The input router with the real gate."""
    from etlhub.core.dependencies import get_input_upload_service, get_pipeline_gate
    from etlhub.application.use_cases.input_upload_service import InputUploadService

    app.dependency_overrides[get_input_upload_service] = lambda: InputUploadService(tmp_path / "input", get_pipeline_gate())
    yield app
    app.dependency_overrides.pop(get_input_upload_service)


def test_checkpoints_of_a_new_cycle(client):
    body = client.get("/pipeline/checkpoints").json()

    assert (body["current_step"], body["cycle_state"], body["run"], body["lock"]) == ("data_import", "open", None, None)
    assert [s["accessible"] for s in body["steps"]] == [True, False, False]
    assert body["steps"][0]["items"][0]["launchable"] is True


def test_checkpoints_rejects_a_bad_cycle(client):
    assert client.get("/pipeline/checkpoints", params={"cycle": "2026-10"}).status_code == 422


def test_launching_out_of_order_is_refused_with_409(client, queue):
    response = client.post("/build_analytics")

    assert response.status_code == 409
    assert "data_import/import_gee" in response.json()["message"]
    assert queue == []


def test_a_run_job_without_an_open_run_is_refused(client, checkpoint_store, queue):
    _import(checkpoint_store)

    response = client.post("/fetch_climate")

    assert response.status_code == 409
    assert "open forecast run" in response.json()["message"]


def test_runs_open_one_at_a_time_and_can_be_abandoned(client, checkpoint_store):
    _import(checkpoint_store)

    opened = client.post("/pipeline/runs", json={"source": "CSB", "disease": "Malaria"})
    second = client.post("/pipeline/runs", json={"source": "COM", "disease": "Malaria"})
    abandoned = client.delete("/pipeline/runs/current")

    assert opened.status_code == 201
    assert (opened.json()["disease_code"], opened.json()["ou_level"]) == ("pridec_historic_CSBMalaria", "5")
    assert second.status_code == 409
    assert abandoned.json() == {"abandoned": "CSB/Malaria"}


def test_runs_reject_an_unknown_couple(client):
    assert client.post("/pipeline/runs", json={"source": "XYZ", "disease": "Malaria"}).status_code == 422


def test_approve_through_the_api(client, checkpoint_store):
    _import(checkpoint_store)
    _prepare(checkpoint_store, "COM/Malaria")

    response = client.post("/pipeline/runs/current/approve", json={"decision": "approve"})

    assert response.json() == {"couple": "COM/Malaria", "decision": "approve"}
    assert client.post("/pipeline/runs/current/approve", json={"decision": "maybe"}).status_code == 422


def test_relaunch_of_a_success_returns_the_impact_then_accepts_confirm(client, checkpoint_store, queue):
    checkpoint_store.start("import_gee", "first")
    checkpoint_store.finish("first", "success")

    refused = client.post("/import_gee")
    accepted = client.post("/import_gee", params={"confirm": "true"})

    assert refused.status_code == 409
    assert refused.json()["code"] == "confirmation_required"
    assert refused.json()["impact"]["blocked_steps"] == ["forecast", "system_update"]
    assert accepted.status_code == 202
    assert len(queue) == 1
    assert "confirm" not in queue[0][1]  # confirm stops at the gate, it is not sent to the task


def test_upload_without_a_run_is_refused_and_writes_nothing(upload_app, tmp_path, checkpoint_store):
    _import(checkpoint_store)

    response = TestClient(upload_app).post("/input/files/config", files={"file": ("c.json", b"{}")})

    assert response.status_code == 409
    assert not (tmp_path / "input" / "config.json").exists()


def test_config_for_another_month_is_refused_with_422(upload_app, tmp_path, checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")

    response = TestClient(upload_app).post("/input/files/config", files={"file": ("c.json", b'{"forecast_start": "199001"}')})

    assert response.status_code == 422
    assert "199001" in response.json()["detail"]
    assert not (tmp_path / "input" / "config.json").exists()


def test_calc_orgunit_alerts_is_not_implemented(client):
    response = client.post("/calc_orgunit_alerts")

    assert response.status_code == 501
    assert "not implemented" in response.json()["message"]


def test_release_lock(client, checkpoint_store):
    checkpoint_store.start("import_gee", "dead")

    assert client.delete("/pipeline/lock").json() == {"released": "dead"}
    assert client.get("/pipeline/checkpoints").json()["lock"] is None


def test_a_task_end_records_the_checkpoint_and_frees_the_lock(checkpoint_store, queue):
    checkpoint_store.start("import_gee", "import_gee_ok")

    tasks._run_task("import_gee_ok", "GEE import", lambda **kwargs: None)

    state = checkpoint_store.progress()
    assert state["steps"][0]["items"][0]["status"] == "success"
    assert state["lock"] is None


def test_a_failed_task_records_error_and_frees_the_lock(checkpoint_store, queue):
    checkpoint_store.start("import_gee", "import_gee_ko")

    def fail(**kwargs):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        tasks._run_task("import_gee_ko", "GEE import", fail)

    state = checkpoint_store.progress()
    assert state["steps"][0]["items"][0]["status"] == "error"
    assert state["lock"] is None


def test_a_queueing_failure_frees_the_lock(checkpoint_store, monkeypatch):
    monkeypatch.setattr(tasks, "JobStore", InMemoryJobStore)

    def broker_down(*args, **kwargs):
        raise ConnectionError("broker down")

    monkeypatch.setattr(tasks.task_etl, "delay", broker_down)

    with pytest.raises(ConnectionError):
        tasks.CeleryTaskLauncher().launch("import_gee", "import_gee_1")

    state = checkpoint_store.progress()
    assert state["lock"] is None
    assert state["steps"][0]["items"][0]["status"] == "error"


def test_mode_switch_through_the_api(client, checkpoint_store):
    assert client.put("/pipeline/mode", json={"dry_run": True}).json() == {"dry_run": True}
    _import(checkpoint_store)

    refused = client.put("/pipeline/mode", json={"dry_run": False})
    accepted = client.put("/pipeline/mode", json={"dry_run": False}, params={"confirm": "true"})

    assert refused.status_code == 409 and refused.json()["code"] == "confirmation_required"
    assert accepted.json() == {"dry_run": False}
    assert client.get("/pipeline/checkpoints").json()["dry_run"] is False
