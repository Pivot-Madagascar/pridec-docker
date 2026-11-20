"""The pipeline gate seen from the API and from the Celery tasks (real gate, temporary db)."""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from etlhub.infrastructure import tasks
from tests.infrastructure.test_checkpoint_store import _import, _prepare


@pytest.fixture
def queue(monkeypatch, job_store):
    """Celery replaced: records the queued jobs."""
    monkeypatch.setattr(tasks, "JobStore", lambda: job_store)
    queued = []
    monkeypatch.setattr(tasks.task_etl, "apply_async", lambda args, kwargs, task_id: queued.append((args[1:], kwargs)))
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

    assert (body["current_step"], body["run"], body["lock"]) == ("data_import", None, None)
    assert [s["accessible"] for s in body["steps"]] == [True, False, False]
    assert body["steps"][0]["items"][0]["launchable"] is True


def test_checkpoints_rejects_a_bad_pass_id(client):
    assert client.get("/pipeline/checkpoints", params={"pass_id": "2026-10"}).status_code == 422


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


@pytest.fixture
def fetched(tmp_path, monkeypatch, checkpoint_store, job_store):
    """Both Pivot imports done; COMMalaria (flagged) and CSBMalaria fetched; the posts recorded instead of sent."""
    from etlhub.application.use_cases import fetch_pivot
    for task in ("import_pivot_com", "import_pivot_csb"):
        checkpoint_store.start(task, task)
        checkpoint_store.finish(task, "success")
    out = tmp_path / "temp_fetch"
    out.mkdir()
    for name, flags in (("pridec_historic_COMMalaria", {"text": None, "flagged": True, "error": "too many"}),
                        ("pridec_historic_CSBMalaria", {"text": "numNA: 0", "flagged": False, "error": None})):
        (out / f"{name}_fetched.json").write_text(json.dumps({"dataValues": [{"dataElement": name, "value": 5}]}))
        (out / f"{name}_flags.json").write_text(json.dumps(flags))
    posts = []
    monkeypatch.setattr(fetch_pivot, "fetch_dir", lambda: out)
    monkeypatch.setattr(fetch_pivot, "setup_logging", lambda: None)
    monkeypatch.setattr(fetch_pivot, "get_dhis_url", lambda: "https://dhis2.test")
    monkeypatch.setattr(fetch_pivot, "get_dhis_token", lambda: "t")
    monkeypatch.setattr(fetch_pivot, "post_dataElements", lambda **kw: posts.append(kw) or SimpleNamespace(
        json=lambda: {"status": "OK", "response": {"status": "SUCCESS", "importCount": {"imported": 1}}}))
    return posts


def _approve_imports(client):
    return next(i for i in client.get("/pipeline/checkpoints").json()["steps"][0]["items"] if i["item"] == "approve_imports")


def test_imports_lists_the_fetched_elements_with_their_check(client, fetched):
    imports = client.get("/pipeline/imports/fetched").json()["imports"]

    assert [i["task"] for i in imports] == ["import_pivot_com", "import_pivot_csb"]
    assert imports[0]["elements"] == [{"data_element": "pridec_historic_COMMalaria", "rows": 1, "flagged": True,
                                       "text": None, "error": "too many"}]  # only what was fetched


def test_imports_approval_posts_only_the_chosen_elements_with_the_pass_dry_run(client, checkpoint_store, fetched):
    response = client.post("/pipeline/imports/approve",
                           json={"decision": "approve", "elements": ["pridec_historic_CSBMalaria"]})

    assert response.json()["job_id"].startswith("approve_imports_")
    assert [(p["payload"]["dataValues"][0]["dataElement"], p["dryRun"]) for p in fetched] == [
        ("pridec_historic_CSBMalaria", True)]
    assert _approve_imports(client)["status"] == "success"
    launched = [e for e in checkpoint_store.journal(checkpoint_store.progress()["pass"]["id"])
                if e["event"] == "launched" and e["item"] == "approve_imports"]
    assert launched[0]["detail"]["params"] == {"elements": ["pridec_historic_CSBMalaria"]}
    assert client.post("/pipeline/imports/approve", json={"decision": "approve", "elements": []}).status_code == 409  # confirm


def test_imports_approval_refuses_what_cannot_be_posted(client, fetched):
    def approve(**body):
        return client.post("/pipeline/imports/approve", json={"decision": "approve", **body})

    assert approve().status_code == 422  # elements required
    assert approve(elements=["../../etc/passwd"]).status_code == 422
    assert client.post("/pipeline/imports/approve", json={"decision": "maybe"}).status_code == 422
    assert approve(elements=["pridec_historic_COMRespinf"]).status_code == 409  # not fetched
    assert (fetched, _approve_imports(client)["status"]) == ([], "pending")


def test_imports_approval_with_no_element_posts_nothing_and_reject_undoes_it(client, fetched):
    assert client.post("/pipeline/imports/approve", json={"decision": "approve", "elements": []}).status_code == 200
    assert (fetched, _approve_imports(client)["status"]) == ([], "success")

    assert client.post("/pipeline/imports/approve", json={"decision": "reject"}).json() == {"decision": "reject"}
    assert _approve_imports(client)["status"] == "pending"


def test_a_dhis2_import_error_fails_the_approval(client, fetched, monkeypatch):
    from etlhub.application.use_cases import fetch_pivot
    monkeypatch.setattr(fetch_pivot, "post_dataElements", lambda **kw: SimpleNamespace(
        json=lambda: {"status": "ERROR", "message": "conflicts"}))

    response = client.post("/pipeline/imports/approve",
                           json={"decision": "approve", "elements": ["pridec_historic_CSBMalaria"]})

    assert response.status_code == 500 and "DHIS2 refused pridec_historic_CSBMalaria" in response.json()["message"]
    assert _approve_imports(client)["status"] == "error"


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


def test_the_server_writes_the_chosen_cycle_as_forecast_start_into_config(upload_app, tmp_path, checkpoint_store):
    import json
    checkpoint_store.set_cycle("202001")
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")

    response = TestClient(upload_app).post(
        "/input/files/config", files={"file": ("c.json", b'{"forecast_start": "199001", "month_lag": 3}')})

    assert response.status_code == 200
    written = json.loads((tmp_path / "input" / "config.json").read_text())
    assert written == {"forecast_start": "202001", "month_lag": 3}


def test_calc_orgunit_alerts_is_not_implemented(client):
    response = client.post("/calc_orgunit_alerts")

    assert response.status_code == 501
    assert "not implemented" in response.json()["message"]


class Liveness:
    """TaskLauncher whose is_active answers what the test says (True, False, or None: no worker answered)."""

    def __init__(self, active):
        self.active = active

    def is_active(self, job_id):
        return self.active


@pytest.fixture
def lock_held(app, checkpoint_store, job_store):
    from etlhub.core.dependencies import get_job_repository, get_task_launcher
    job_store.set("held", {"job_id": "held", "status": "running"})
    app.dependency_overrides[get_job_repository] = lambda: job_store
    checkpoint_store.start("import_gee", "held")

    def answer(active):
        app.dependency_overrides[get_task_launcher] = lambda: Liveness(active)

    yield answer
    app.dependency_overrides.pop(get_job_repository)
    app.dependency_overrides.pop(get_task_launcher, None)


def test_release_lock_of_a_dead_job_needs_no_confirmation(client, lock_held, job_store):
    lock_held(False)

    assert client.delete("/pipeline/lock").json() == {"released": "held"}
    assert client.get("/pipeline/checkpoints").json()["lock"] is None
    # Its end is seen by the toast and the tracking: no job left "running" for 24 h
    assert job_store.get("held")["status"] == "error"


@pytest.mark.parametrize("active", [True, None])
def test_release_lock_of_a_job_that_may_still_run_asks_for_confirmation(client, lock_held, job_store, active):
    lock_held(active)

    refused = client.delete("/pipeline/lock")

    assert refused.status_code == 409
    assert refused.json()["code"] == "confirmation_required"
    assert refused.json()["impact"] == {"job_id": "held", "task": "import_gee", "active": active}
    assert client.get("/pipeline/checkpoints").json()["lock"]["job_id"] == "held"  # nothing released
    assert job_store.get("held")["status"] == "running"

    assert client.delete("/pipeline/lock", params={"confirm": True}).json() == {"released": "held"}
    assert job_store.get("held")["status"] == "error"


def test_release_lock_of_the_other_modes_job_never_names_it(client, lock_held, job_store, checkpoint_store):
    asked = []
    lock_held(True)
    from etlhub.core.dependencies import get_task_launcher
    client.app.dependency_overrides[get_task_launcher] = lambda: SimpleNamespace(is_active=lambda j: asked.append(j) or True)
    checkpoint_store.mode["test_mode"] = True  # "held" is a production job; this user is in test mode

    refused = client.delete("/pipeline/lock")

    assert refused.status_code == 409
    assert refused.json()["impact"] == {"job_id": None, "task": "a job of the other mode", "active": True}
    assert "held" not in refused.json()["message"] and asked == ["held"]  # the workers are asked about the real job
    assert client.delete("/pipeline/lock", params={"confirm": True}).json() == {"released": None}  # never named
    assert client.get("/pipeline/checkpoints").json()["lock"] is None
    assert job_store.get("held")["status"] == "error"


def test_release_lock_without_lock(client, app):
    from etlhub.core.dependencies import get_task_launcher
    app.dependency_overrides[get_task_launcher] = lambda: Liveness(True)

    assert client.delete("/pipeline/lock").json() == {"released": None}
    app.dependency_overrides.pop(get_task_launcher)


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


def test_a_queueing_failure_frees_the_lock(checkpoint_store, monkeypatch, job_store):
    monkeypatch.setattr(tasks, "JobStore", lambda: job_store)

    def broker_down(*args, **kwargs):
        raise ConnectionError("broker down")

    monkeypatch.setattr(tasks.task_etl, "apply_async", broker_down)

    with pytest.raises(ConnectionError):
        tasks.CeleryTaskLauncher().launch("import_gee", "import_gee_1")

    state = checkpoint_store.progress()
    assert state["lock"] is None
    assert state["steps"][0]["items"][0]["status"] == "error"


def test_the_mode_is_switched_in_the_callers_session_only(app):
    from types import SimpleNamespace
    from etlhub.core.dependencies import get_auth_store
    sessions = {"mine": False}

    def set_session_mode(session_id, test_mode):
        return session_id in sessions and not sessions.update({session_id: test_mode})

    app.dependency_overrides[get_auth_store] = lambda: SimpleNamespace(set_session_mode=set_session_mode)
    try:
        client = TestClient(app, cookies={"etlhub_session": "mine"})
        assert client.put("/pipeline/mode", json={"test_mode": True}).json() == {"test_mode": True}
        assert sessions == {"mine": True}  # this session only: nothing global
        assert client.put("/pipeline/mode", json={"test_mode": True, "pass_action": "later"}).status_code == 422
        gone = TestClient(app, cookies={"etlhub_session": "expired"})
        assert gone.put("/pipeline/mode", json={"test_mode": False}).status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_store, None)


def test_switching_mode_mid_pass_asks_first_then_pauses_or_abandons_it(app, checkpoint_store):
    from etlhub.core.dependencies import get_auth_store
    sessions = {"mine": False}
    app.dependency_overrides[get_auth_store] = lambda: SimpleNamespace(
        set_session_mode=lambda sid, test_mode: not sessions.update({sid: test_mode}))
    _import(checkpoint_store)  # a production pass is active
    client = TestClient(app, cookies={"etlhub_session": "mine"})
    try:
        asked = client.put("/pipeline/mode", json={"test_mode": True})
        assert asked.status_code == 409 and asked.json()["code"] == "confirmation_required"
        assert asked.json()["impact"]["actions"] == ["pause", "abandon"]
        assert sessions == {"mine": False}  # not switched before the choice

        assert client.put("/pipeline/mode", json={"test_mode": False}).json() == {"test_mode": False}  # same mode: nothing
        assert client.put("/pipeline/mode", json={"test_mode": True, "pass_action": "abandon"}).json() == {"test_mode": True}
        assert sessions == {"mine": True}
        assert checkpoint_store.progress()["pass"]["state"] == "abandoned"
    finally:
        app.dependency_overrides.pop(get_auth_store, None)


def test_a_request_is_served_in_the_mode_of_its_session(anon_app, monkeypatch, checkpoint_store):
    from etlhub.api.auth import dhis2_auth
    from etlhub.core.job_context import current_test_mode
    seen = []
    monkeypatch.setattr(checkpoint_store, "_test_mode", lambda: seen.append(current_test_mode()) or current_test_mode())
    for test_mode in (True, False):
        monkeypatch.setattr(dhis2_auth, "session_from_cookies",
                            lambda cookies, t=test_mode: {"user": {"username": "jdoe"}, "test_mode": t})
        assert TestClient(anon_app).get("/pipeline/checkpoints").json()["test_mode"] is test_mode


def test_cycle_choice_through_the_api(client):
    assert client.put("/pipeline/cycle", json={"cycle": "2026-09"}).status_code == 422
    assert client.put("/pipeline/cycle", json={"cycle": "202613"}).status_code == 422
    assert client.put("/pipeline/cycle", json={"cycle": "299901"}).status_code == 409

    assert client.put("/pipeline/cycle", json={"cycle": "202001"}).json() == {"cycle": "202001"}
    assert client.get("/pipeline/checkpoints").json()["cycle"] == "202001"
    client.put("/pipeline/cycle", json={"cycle": None})
    assert client.get("/pipeline/checkpoints").json()["cycle"] != "202001"


def test_any_user_unlocks_and_abandons_a_run(client, checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")

    assert client.delete("/pipeline/lock").json() == {"released": None}  # no roles since 2026-11-17
    assert client.delete("/pipeline/runs/current").json() == {"abandoned": "COM/Malaria"}


def test_the_report_of_a_closed_run(client, checkpoint_store, tmp_path):
    _import(checkpoint_store)
    _prepare(checkpoint_store, "COM/Malaria")
    (tmp_path / "output").mkdir(exist_ok=True)
    (tmp_path / "output" / "forecast_report.html").write_text("<p>COM Malaria</p>")
    checkpoint_store.decide("approve")
    checkpoint_store.start("post_forecast", "p")
    checkpoint_store.finish("p", "success")

    report = client.get("/pipeline/runs/COM/Malaria/report")

    assert (report.status_code, report.text) == (200, "<p>COM Malaria</p>")
    assert report.headers["content-type"].startswith("text/html")
    assert client.get("/pipeline/runs/ADJ/Malaria/report").status_code == 404
    assert client.get("/pipeline/runs/XYZ/Malaria/report").status_code == 422


@pytest.fixture
def journal_client(app):
    """The journal reads request_log from the temporary db (conftest `_request_log_db`), not logs/etlhub.db."""
    return TestClient(app)


def test_the_journal_lists_events_with_the_request_that_caused_them(journal_client, queue):
    journal_client.post("/import_gee")  # the first launch starts the pass
    pass_id = journal_client.get("/pipeline/checkpoints").json()["pass"]["id"]

    events = journal_client.get(f"/pipeline/passes/{pass_id}/journal").json()

    assert [(e["event"], e["mode"]) for e in events] == [("pass_started", "production")]  # the launch: still running
    assert (events[0]["request"]["method"], events[0]["request"]["status_code"]) == ("POST", 202)
    assert journal_client.get("/pipeline/passes/2026-10/journal").status_code == 422


def test_the_journal_csv(journal_client, queue):
    journal_client.post("/import_gee")
    pass_id = journal_client.get("/pipeline/checkpoints").json()["pass"]["id"]

    response = journal_client.get(f"/pipeline/passes/{pass_id}/journal.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.splitlines()[0].startswith("at,mode,cycle,pass_id,step,item,event,actor")


def test_the_logged_in_user_is_the_actor_of_the_events(anon_app, monkeypatch, checkpoint_store):
    from etlhub.api.auth import dhis2_auth
    from etlhub.infrastructure.checkpoint_store import get_checkpoint_store
    monkeypatch.setattr(dhis2_auth, "session_from_cookies", lambda cookies: {"user": {"username": "jdoe"}, "test_mode": False})
    checkpoint_store.start("import_gee", "g")
    checkpoint_store.finish("g", "success")

    paused = TestClient(anon_app).post("/pipeline/passes/current/pause").json()

    assert [(e["event"], e["actor"]) for e in get_checkpoint_store().journal(paused["id"])][-1] == ("paused", "jdoe")


def test_pause_resume_and_abandon_through_the_api(client, checkpoint_store):
    checkpoint_store.start("import_gee", "g")
    checkpoint_store.finish("g", "success")

    paused = client.post("/pipeline/passes/current/pause").json()
    assert paused["state"] == "paused"
    assert client.post("/pipeline/passes/current/pause").status_code == 409  # nothing active any more
    assert client.post(f"/pipeline/passes/{paused['id']}/resume").json()["state"] == "active"
    assert client.post(f"/pipeline/passes/{paused['id']}/abandon").json()["state"] == "abandoned"
    refused = client.post(f"/pipeline/passes/{paused['id']}/resume")
    assert (refused.status_code, refused.json()["message"]) == (409, f"Pass {paused['id']} is abandoned: it cannot be resumed")
    assert client.post("/pipeline/passes/nothex!/resume").status_code == 422


def test_a_new_pass_starts_at_once_and_after_a_pause_with_confirm(client, checkpoint_store):
    first = client.post("/pipeline/passes")
    assert (first.status_code, first.json()["state"]) == (201, "active")
    client.post("/pipeline/passes/current/pause")

    refused = client.post("/pipeline/passes")
    assert (refused.status_code, refused.json()["code"]) == (409, "confirmation_required")
    assert refused.json()["impact"]["paused_pass"] == first.json()["id"]
    second = client.post("/pipeline/passes", params={"confirm": "true"}).json()
    assert second["id"] != first.json()["id"]
    assert client.get("/pipeline/checkpoints").json()["pass"]["id"] == second["id"]



def test_a_new_pass_keeps_the_gee_variables_chosen_on_home(client, checkpoint_store, monkeypatch):
    import sys
    monkeypatch.setattr(sys.modules["pridec_gee"], "AVAILABLE_VARIABLES", ["a_1", "b_2", "c_3"])  # a MagicMock here

    for chosen, message in (([], "Choose at least one GEE variable"), (["a_1", "nope"], "Unknown GEE variables: nope")):
        refused = client.post("/pipeline/passes", json={"gee_variables": chosen})
        assert (refused.status_code, refused.json()["message"]) == (400, message)
    assert client.get("/pipeline/checkpoints").json()["pass"] is None  # nothing started

    started = client.post("/pipeline/passes", json={"gee_variables": ["c_3", "a_1"]}).json()
    assert started["gee_variables"] == "a_1,c_3"  # pridec_gee's order: equal choices, equal import parameters
    assert (started["dry_run"], started["dhis_url"]) == (True, "https://dhis2.test")  # the rest fixed too
    assert checkpoint_store.pass_config()["gee_variables"] == "a_1,c_3"
    client.post("/pipeline/passes/current/pause")
    every = client.post("/pipeline/passes", params={"confirm": "true"}, json={"dry_run": False}).json()  # all of them
    assert (every["gee_variables"], every["dry_run"]) == ("a_1,b_2,c_3", False)


def test_the_import_parameters_of_a_new_pass_carry_its_gee_variables():
    from etlhub.application.use_cases.ingestion_service import current_import_params
    plan = lambda: {"dhis_url": "u", "imports": [{"task": "import_gee", "elements": ["a_1", "b_2"]},
                                                 {"task": "import_pivot_com", "elements": ["x"]}]}

    params = current_import_params(plan, gee_variables=["b_2"])

    assert (params["import_gee"]["elements"], params["import_pivot_com"]["elements"]) == (["b_2"], ["x"])
    assert current_import_params(plan)["import_gee"]["elements"] == ["a_1", "b_2"]  # a launch: the active pass's


def test_the_csv_keeps_the_event_job_id_and_adds_the_request():
    import csv
    from types import SimpleNamespace
    from etlhub.application.use_cases.journal_service import JournalService
    event = {"cycle": "202610", "at": "t", "step": "forecast", "item": "config/Malaria", "event": "uploaded",
             "job_id": "upload_config_1", "actor": "jdoe", "request_id": "r1", "detail": None, "mode": "production"}
    request = {"request_id": "r1", "method": "POST", "url": "/input/files/config", "status_code": 200, "job_id": None}
    service = JournalService(SimpleNamespace(journal=lambda cycle: [event]),
                             SimpleNamespace(get_many=lambda ids: {"r1": request}))

    (row,) = csv.DictReader(service.csv("202610").splitlines())

    assert (row["job_id"], row["method"], row["status_code"]) == ("upload_config_1", "POST", "200")


def test_the_cycles_route_lists_the_target_cycle(client):
    from etlhub.domain.pipeline import this_month

    assert client.get("/pipeline/cycles").json() == [{"cycle": this_month(), "target": True, "passes": []}]


def test_journal_shows_a_job_once_at_its_end_with_its_launch_request():
    from etlhub.application.use_cases.journal_service import _job_outcomes

    def ev(event, job_id, actor="worker", request_id=None, detail=None):
        return {"event": event, "job_id": job_id, "actor": actor, "request_id": request_id, "detail": detail}

    events = [ev("launched", "a", "alice", "req-a", {"confirm": True}), ev("succeeded", "a"),
              ev("launched", "b", "bob", "req-b"),  # still running
              ev("launched", "c", "carol", "req-c"), ev("lock_released", "c", "admin", "req-x"),
              ev("uploaded", None, "alice", "req-u")]

    assert _job_outcomes(events) == [ev("succeeded", "a", "alice", "req-a", {"confirm": True}),
                                     ev("launched", "c", "carol", "req-c"), ev("lock_released", "c", "admin", "req-x"),
                                     ev("uploaded", None, "alice", "req-u")]


def test_a_dhis2_job_takes_the_dryrun_of_its_launch_and_journals_it(client, checkpoint_store, monkeypatch, job_store):
    monkeypatch.setattr(tasks, "JobStore", lambda: job_store)
    queued = []
    monkeypatch.setattr(tasks.task_etl, "apply_async", lambda args, kwargs, task_id: queued.append(kwargs))
    checkpoint_store.mode["dry_run"] = True  # .env

    assert client.post("/import_gee", params={"dry_run": False}).status_code == 202

    assert queued[0]["dry_run"] is False
    events = checkpoint_store.journal(checkpoint_store.progress()["pass"]["id"])
    assert [e["detail"]["dry_run"] for e in events if e["event"] == "launched"] == [False]


def test_a_job_gets_the_configuration_of_its_pass_with_its_launch(client, checkpoint_store, monkeypatch, job_store):
    monkeypatch.setattr(tasks, "JobStore", lambda: job_store)
    queued = []
    monkeypatch.setattr(tasks.task_etl, "apply_async", lambda args, kwargs, task_id: queued.append(kwargs))
    checkpoint_store.start_pass(gee_variables="v1", dry_run=True)

    launched = client.post("/import_gee")
    checkpoint_store.finish(launched.json()["job_id"], "success")
    refused = client.post("/import_gee", params={"dry_run": False, "confirm": True})

    assert queued[0]["pass_config"] == {"gee_variables": "v1", "parent_ou": "ou_parent", "log_level": "INFO",
                                        "dry_run": True, "dhis_url": "https://dhis2.test"}
    assert (refused.status_code, len(queued)) == (409, 1)
    assert "DRYRUN=true, fixed when it started" in refused.json()["message"]


def test_only_the_jobs_writing_to_dhis2_offer_dry_run(app):
    from etlhub.domain.pipeline import DHIS2_WRITES
    paths = app.openapi()["paths"]
    offered = {path.strip("/") for path, ops in paths.items() for op in ops.values()
               if any(p["name"] == "dry_run" for p in op.get("parameters", []))}

    assert offered == set(DHIS2_WRITES)


def test_update_key_is_refused_in_dry_run_and_nothing_is_written(app, client, checkpoint_store, monkeypatch):
    from etlhub.application.use_cases import analytics_service
    ran = []
    monkeypatch.setattr(analytics_service, "run_etl_job", lambda *args, **kwargs: ran.append(kwargs))
    checkpoint_store.mode["dry_run"] = True  # .env

    for params in ({}, {"dry_run": True}):
        refused = client.post("/update_key", params=params)
        assert refused.status_code == 409
        assert "dry run" in refused.json()["message"]
    assert ran == [] and checkpoint_store.progress()["lock"] is None

    checkpoint_store.start_pass(dry_run=True)  # a pass fixed in dry run never updates the key
    checkpoint_store.mode["dry_run"] = False  # .env changed since: the pass keeps its own
    refused = client.post("/update_key")
    assert (refused.status_code, ran) == (409, [])
    assert "This pass runs in dry run, fixed when it started" in refused.json()["message"]
