import itertools

import pytest

from etlhub.domain.exceptions import ConfirmationRequiredError, PipelineBlockedError
from etlhub.domain.pipeline import COUPLES, PIPELINE, run_items

_ids = itertools.count()


def _pass(store, task, confirm=False):
    job_id = f"{task}_{next(_ids)}"
    store.start(task, job_id, confirm)
    store.finish(job_id, "success")
    return job_id


def _import(store):
    for task in ("import_pivot_csb", "import_gee", "import_pivot_com"):
        _pass(store, task)
    store.decide_imports("approve")
    _pass(store, "build_analytics")


FILES = {"config": "config.json", "external_data": "external_data.csv"}


def _upload(store, name="config", confirm=False, removed=False, content="{}"):
    """What InputUploadService does: write (or delete) the file in input/ inside the gate."""
    path = store._input_dir / FILES[name]
    with store.change_input(name, confirm, removed):
        if removed:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)


def _prepare(store, couple):
    """Opens the run and passes everything up to approve (excluded). Files only in the first run that shares them."""
    store.open_run(couple)
    state = store.progress()
    if _status(state, "forecast", f"config/{couple.split('/')[1]}") != "success":
        _upload(store)
    if _status(state, "forecast", f"external_data/{'csb' if couple.startswith('CSB/') else 'fkt'}") != "success":
        _upload(store, "external_data")
    for task in ("fetch_disease", "fetch_climate", "fetch_geojson", "validate_inputs", "forecast"):
        _pass(store, task)
    if couple.startswith("CSB/"):
        _pass(store, "calc_orgunit_alerts")


def _full_run(store, couple):
    _prepare(store, couple)
    store.decide("approve")
    _pass(store, "post_forecast")


def _step(state, name):
    return next(s for s in state["steps"] if s["step"] == name)


def _status(state, step, item):
    return next(i["status"] for i in _step(state, step)["items"] if i["item"] == item)


@pytest.fixture
def month(monkeypatch):
    """Sets the calendar month seen by the gate."""
    from etlhub.domain import pipeline

    def set_month(value):
        monkeypatch.setattr(pipeline, "this_month", lambda: value)
    set_month("202610")
    return set_month


# --- definition -------------------------------------------------------------------------

def test_the_target_pipeline_has_three_steps_and_71_forecast_items():
    assert list(PIPELINE) == ["data_import", "forecast", "system_update"]
    assert len(PIPELINE["data_import"]) == 5
    assert len(PIPELINE["forecast"]) == 71  # 3 configs + 2 external_data + 6 x 7 + 3 x 8
    assert list(PIPELINE["system_update"]) == ["build_analytics", "update_key"]
    assert len(run_items("COM/Malaria")) == 7
    assert "CSB/Malaria:calc_orgunit_alerts" in run_items("CSB/Malaria")


def test_a_new_cycle_starts_at_data_import(checkpoint_store):
    state = checkpoint_store.progress()

    assert state["current_step"] == "data_import"
    assert state["cycle_state"] == "open"
    assert [s["accessible"] for s in state["steps"]] == [True, False, False]
    assert state["run"] is None and state["lock"] is None


# --- R2, R3, R4 ---------------------------------------------------------------------------

def test_imports_run_in_any_order_and_build_analytics_waits_for_their_approval(checkpoint_store):
    _pass(checkpoint_store, "import_pivot_com")
    with pytest.raises(PipelineBlockedError, match="data_import/import_gee"):
        checkpoint_store.start("build_analytics", "early")
    with pytest.raises(PipelineBlockedError, match="data_import/import_pivot_csb"):
        checkpoint_store.decide_imports("approve")

    for task in ("import_pivot_csb", "import_gee"):
        _pass(checkpoint_store, task)
    with pytest.raises(PipelineBlockedError, match="data_import/approve_imports"):
        checkpoint_store.start("build_analytics", "unapproved")
    checkpoint_store.decide_imports("approve")
    _pass(checkpoint_store, "build_analytics")

    assert _step(checkpoint_store.progress(), "data_import")["done"] is True


def test_rejecting_the_imports_sends_the_approval_back_to_pending(checkpoint_store):
    _import(checkpoint_store)

    checkpoint_store.decide_imports("reject")

    state = checkpoint_store.progress()
    assert _status(state, "data_import", "approve_imports") == "pending"
    assert state["current_step"] == "data_import"


def test_one_job_at_a_time_and_the_lock_never_expires(checkpoint_store):
    checkpoint_store.start("import_gee", "dead")

    with pytest.raises(PipelineBlockedError, match="one job at a time"):
        checkpoint_store.start("import_pivot_com", "next")

    assert checkpoint_store.release_lock() == "dead"
    assert _status(checkpoint_store.progress(), "data_import", "import_gee") == "error"
    checkpoint_store.start("import_pivot_com", "next")


def test_a_failed_step_1_relaunch_blocks_the_forecast_step_but_keeps_its_successes(checkpoint_store):
    _import(checkpoint_store)
    _full_run(checkpoint_store, "COM/Malaria")
    _prepare(checkpoint_store, "ADJ/Diarrhea")

    checkpoint_store.start("import_gee", "rerun", confirm=True)
    checkpoint_store.finish("rerun", "error")

    state = checkpoint_store.progress()
    assert (_step(state, "forecast")["accessible"], state["current_step"]) == (False, "data_import")
    assert _status(state, "forecast", "COM/Malaria:post_forecast") == "success"
    with pytest.raises(PipelineBlockedError, match="step data_import done first"):
        checkpoint_store.decide("approve")

    _pass(checkpoint_store, "import_gee")
    assert _step(checkpoint_store.progress(), "forecast")["accessible"] is True


# --- runs (R6) ----------------------------------------------------------------------------

def test_a_run_needs_data_import_and_only_one_is_open(checkpoint_store):
    with pytest.raises(PipelineBlockedError, match="data_import done first"):
        checkpoint_store.open_run("COM/Malaria")
    _import(checkpoint_store)

    checkpoint_store.open_run("COM/Malaria")

    with pytest.raises(PipelineBlockedError, match="Run COM/Malaria is open"):
        checkpoint_store.open_run("CSB/Malaria")


def test_a_run_job_needs_an_open_run(checkpoint_store):
    _import(checkpoint_store)

    with pytest.raises(PipelineBlockedError, match="open forecast run"):
        checkpoint_store.start("fetch_climate", "orphan")


def test_items_of_a_run_follow_their_prerequisites(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    _pass(checkpoint_store, "fetch_disease")

    with pytest.raises(PipelineBlockedError, match="config/Malaria"):
        checkpoint_store.start("validate_inputs", "v")
    with pytest.raises(PipelineBlockedError, match="COM/Malaria:approve"):
        checkpoint_store.start("post_forecast", "p")
    with pytest.raises(PipelineBlockedError, match="not part of run COM/Malaria"):
        checkpoint_store.start("calc_orgunit_alerts", "c")


def test_opening_a_run_empties_input_and_output(checkpoint_store, tmp_path):
    _import(checkpoint_store)
    (tmp_path / "input").mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "input" / "disease_data.json").write_text("{}")
    (tmp_path / "output" / "forecast.json").write_text("{}")

    checkpoint_store.open_run("COM/Malaria")

    assert list((tmp_path / "input").iterdir()) == []
    assert list((tmp_path / "output").iterdir()) == []


def test_run_jobs_get_the_run_context(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("CSB/Respinf")

    _pass(checkpoint_store, "fetch_disease")

    assert checkpoint_store.contexts[-1] == {
        "DISEASE_CODE": "pridec_historic_CSBRespinf", "OU_LEVEL": "5", "ALERT_NAME": "CSBRespinfVigilance",
    }


def test_post_forecast_closes_the_run_and_a_closed_couple_reopens_only_with_confirm(checkpoint_store):
    _import(checkpoint_store)
    _full_run(checkpoint_store, "COM/Malaria")
    assert checkpoint_store.progress()["run"] is None

    with pytest.raises(ConfirmationRequiredError) as refused:
        checkpoint_store.open_run("COM/Malaria")
    assert "COM/Malaria:post_forecast" in refused.value.impact["reset_items"]

    checkpoint_store.open_run("COM/Malaria", confirm=True)
    assert _status(checkpoint_store.progress(), "forecast", "COM/Malaria:post_forecast") == "pending"


def test_closing_a_run_archives_its_report(checkpoint_store, tmp_path):
    _import(checkpoint_store)
    _prepare(checkpoint_store, "COM/Malaria")
    (tmp_path / "output").mkdir(exist_ok=True)
    (tmp_path / "output" / "forecast_report.html").write_text("<p>COM Malaria</p>")
    checkpoint_store.decide("approve")
    _pass(checkpoint_store, "post_forecast")

    checkpoint_store.open_run("ADJ/Malaria")  # empties output/

    cycle = checkpoint_store.progress()["cycle"]
    assert checkpoint_store.report(cycle, "COM/Malaria").read_text() == "<p>COM Malaria</p>"
    assert checkpoint_store.report(cycle, "ADJ/Malaria") is None


def test_abandoning_a_run_resets_its_items(checkpoint_store):
    _import(checkpoint_store)
    _prepare(checkpoint_store, "ADJ/Malaria")

    assert checkpoint_store.abandon_run() == "ADJ/Malaria"

    state = checkpoint_store.progress()
    assert state["run"] is None
    assert _status(state, "forecast", "ADJ/Malaria:forecast") == "pending"
    checkpoint_store.open_run("ADJ/Malaria")  # an abandoned couple reopens without confirmation


# --- approval -----------------------------------------------------------------------------

def test_approve_needs_the_forecast_and_reject_resets_it(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Diarrhea")
    with pytest.raises(PipelineBlockedError, match="COM/Diarrhea:"):
        checkpoint_store.decide("approve")
    with pytest.raises(PipelineBlockedError, match="Nothing to reject"):
        checkpoint_store.decide("reject")
    checkpoint_store.abandon_run()

    _prepare(checkpoint_store, "COM/Diarrhea")
    checkpoint_store.decide("reject")

    state = checkpoint_store.progress()
    assert _status(state, "forecast", "COM/Diarrhea:forecast") == "pending"
    assert _status(state, "forecast", "COM/Diarrhea:validate_inputs") == "success"
    _pass(checkpoint_store, "forecast")  # redone without confirmation
    checkpoint_store.decide("approve")
    assert _status(checkpoint_store.progress(), "forecast", "COM/Diarrhea:approve") == "success"


def test_a_csb_run_needs_calc_orgunit_alerts_before_approval(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("CSB/Malaria")
    _upload(checkpoint_store)
    _upload(checkpoint_store, "external_data")
    for task in ("fetch_disease", "fetch_climate", "fetch_geojson", "validate_inputs", "forecast"):
        _pass(checkpoint_store, task)

    with pytest.raises(PipelineBlockedError, match="CSB/Malaria:calc_orgunit_alerts"):
        checkpoint_store.decide("approve")

    assert checkpoint_store.skip_alerts() == "CSB/Malaria"  # temporary, until the script exists
    checkpoint_store.decide("approve")
    assert _status(checkpoint_store.progress(), "forecast", "CSB/Malaria:approve") == "success"


def test_skip_alerts_is_refused_outside_a_csb_run(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    with pytest.raises(PipelineBlockedError, match="CSB runs only"):
        checkpoint_store.skip_alerts()


# --- input files ------------------------------------------------------------------------

def test_input_files_need_an_open_run(checkpoint_store):
    _import(checkpoint_store)

    with pytest.raises(PipelineBlockedError, match="open forecast run"):
        _upload(checkpoint_store)
    with pytest.raises(PipelineBlockedError, match="open forecast run"):
        _upload(checkpoint_store, "external_data")


def test_config_is_free_to_replace_until_validate_inputs_succeeds(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    _upload(checkpoint_store)
    _upload(checkpoint_store)  # no confirmation: nothing validated yet
    _upload(checkpoint_store, "external_data")
    for task in ("fetch_disease", "fetch_climate", "fetch_geojson", "validate_inputs"):
        _pass(checkpoint_store, task)

    with pytest.raises(ConfirmationRequiredError) as refused:
        _upload(checkpoint_store)
    assert refused.value.impact["reset_items"] == ["COM/Malaria:validate_inputs"]

    _upload(checkpoint_store, confirm=True)
    state = checkpoint_store.progress()
    assert _status(state, "forecast", "config/Malaria") == "success"
    assert _status(state, "forecast", "COM/Malaria:validate_inputs") == "pending"


def test_deleting_config_resets_it(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    _upload(checkpoint_store)

    _upload(checkpoint_store, removed=True)

    assert _status(checkpoint_store.progress(), "forecast", "config/Malaria") == "pending"


def test_external_data_is_a_mandatory_item_per_level(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("ADJ/Respinf")
    _upload(checkpoint_store)
    for task in ("fetch_disease", "fetch_climate", "fetch_geojson"):
        _pass(checkpoint_store, task)
    with pytest.raises(PipelineBlockedError, match="external_data/fkt"):
        checkpoint_store.start("validate_inputs", "v")
    _upload(checkpoint_store, "external_data")
    _pass(checkpoint_store, "validate_inputs")

    with pytest.raises(ConfirmationRequiredError):
        _upload(checkpoint_store, "external_data")
    _upload(checkpoint_store, "external_data", confirm=True)
    state = checkpoint_store.progress()
    assert _status(state, "forecast", "external_data/fkt") == "success"
    assert _status(state, "forecast", "ADJ/Respinf:validate_inputs") == "pending"

    _upload(checkpoint_store, "external_data", removed=True)
    assert _status(checkpoint_store.progress(), "forecast", "external_data/fkt") == "pending"


def test_a_failed_upload_marks_config_error_and_frees_the_lock(checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")

    with pytest.raises(OSError):
        with checkpoint_store.change_input("config"):
            raise OSError("disk full")

    state = checkpoint_store.progress()
    assert _status(state, "forecast", "config/Malaria") == "error"
    assert state["lock"] is None


def test_an_upload_that_fails_after_the_write_frees_the_lock(checkpoint_store, monkeypatch):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")

    def keep_fails(*args):
        raise PermissionError("uploads/ is not writable")
    monkeypatch.setattr(checkpoint_store, "_keep", keep_fails)

    with pytest.raises(PermissionError):
        _upload(checkpoint_store)

    state = checkpoint_store.progress()
    assert _status(state, "forecast", "config/Malaria") == "error"
    assert state["lock"] is None


# --- R5 -----------------------------------------------------------------------------------

def test_relaunching_a_success_in_a_run_needs_confirm_and_resets_its_dependents(checkpoint_store):
    _import(checkpoint_store)
    _prepare(checkpoint_store, "COM/Respinf")
    before = checkpoint_store.progress()

    with pytest.raises(ConfirmationRequiredError) as refused:
        checkpoint_store.start("fetch_climate", "again")

    assert refused.value.impact["reset_items"] == ["COM/Respinf:validate_inputs", "COM/Respinf:forecast"]
    assert refused.value.impact["blocked_steps"] == ["system_update"]
    assert checkpoint_store.progress() == before  # a refusal writes nothing

    checkpoint_store.start("fetch_climate", "again", confirm=True)
    state = checkpoint_store.progress()
    assert _status(state, "forecast", "COM/Respinf:fetch_climate") == "running"
    assert _status(state, "forecast", "COM/Respinf:forecast") == "pending"


def test_an_item_in_error_relaunches_without_confirmation(checkpoint_store):
    checkpoint_store.start("import_gee", "ko")
    checkpoint_store.finish("ko", "error")

    checkpoint_store.start("import_gee", "retry")

    assert _status(checkpoint_store.progress(), "data_import", "import_gee") == "running"


# --- build_analytics and the cycle ------------------------------------------------------

def _all_runs(store):
    _import(store)
    for couple in COUPLES:
        _full_run(store, couple)


def test_build_analytics_fills_its_two_slots_in_order(checkpoint_store):
    _all_runs(checkpoint_store)

    second = _pass(checkpoint_store, "build_analytics")

    update = {i["item"]: i["job_id"] for i in _step(checkpoint_store.progress(), "system_update")["items"]}
    assert update["build_analytics"] == second
    with pytest.raises(ConfirmationRequiredError):  # both in success: a relaunch of the last
        checkpoint_store.start("build_analytics", "third")


def test_the_whole_cycle_completes_then_closes_until_next_month(checkpoint_store, month):
    _all_runs(checkpoint_store)
    for task in ("build_analytics", "update_key"):
        _pass(checkpoint_store, task)

    state = checkpoint_store.progress()
    assert (state["current_step"], state["cycle_state"]) == (None, "closed")
    with pytest.raises(PipelineBlockedError, match="202610 is complete"):
        checkpoint_store.start("import_gee", "again")

    month("202611")
    checkpoint_store.start("import_gee", "next_cycle")
    assert checkpoint_store.progress()["cycle"] == "202611"


def test_a_new_month_starts_a_new_cycle_and_abandons_the_open_run(checkpoint_store, month):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    month("202611")

    _pass(checkpoint_store, "import_gee")  # no confirmation: the switch is automatic

    state = checkpoint_store.progress()
    assert (state["cycle"], state["run"]) == ("202611", None)
    old = checkpoint_store.progress("202610")
    assert old["cycle_state"] == "open"  # unfinished, kept as history
    assert old["run"] is None  # COM/Malaria was abandoned, not left open
    assert _step(old, "data_import")["done"] is True


def test_a_chosen_cycle_takes_the_launches_until_set_back_to_the_calendar_month(checkpoint_store, month):
    with pytest.raises(PipelineBlockedError, match="future"):
        checkpoint_store.set_cycle("202611")

    assert checkpoint_store.set_cycle("202609") == {"cycle": "202609"}
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    assert checkpoint_store.progress()["cycle"] == "202609"
    assert _step(checkpoint_store.progress("202610"), "data_import")["done"] is False
    with pytest.raises(PipelineBlockedError, match="COM/Malaria is open"):
        checkpoint_store.set_cycle(None)

    month("202611")  # a chosen cycle does not follow the calendar: its run stays open
    assert checkpoint_store.progress()["run"]["couple"] == "COM/Malaria"

    checkpoint_store.abandon_run()
    assert checkpoint_store.set_cycle("202611") == {"cycle": "202611"}  # the calendar month: follow it again
    month("202612")
    assert checkpoint_store.progress()["cycle"] == "202612"


def test_a_complete_cycle_can_be_chosen_but_takes_no_launch(checkpoint_store, month):
    _all_runs(checkpoint_store)
    for task in ("build_analytics", "update_key"):
        _pass(checkpoint_store, task)
    month("202611")

    checkpoint_store.set_cycle("202610")

    assert checkpoint_store.progress()["cycle_state"] == "closed"
    with pytest.raises(PipelineBlockedError, match="202610 is complete"):
        checkpoint_store.start("import_gee", "again")


# --- files shared between runs ----------------------------------------------------------

def test_a_disease_config_is_uploaded_once_and_restored_for_its_other_runs(checkpoint_store, tmp_path):
    _import(checkpoint_store)
    checkpoint_store.open_run("ADJ/Malaria")
    _upload(checkpoint_store, content='{"disease": "malaria"}')
    checkpoint_store.abandon_run()

    checkpoint_store.open_run("CSB/Malaria")

    assert (tmp_path / "input" / "config.json").read_text() == '{"disease": "malaria"}'
    assert _status(checkpoint_store.progress(), "forecast", "config/Malaria") == "success"
    checkpoint_store.abandon_run()
    checkpoint_store.open_run("COM/Diarrhea")  # another disease: its own config, nothing restored
    assert not (tmp_path / "input" / "config.json").exists()


def test_external_data_is_kept_per_level(checkpoint_store, tmp_path):
    _import(checkpoint_store)
    checkpoint_store.open_run("ADJ/Malaria")
    _upload(checkpoint_store, "external_data", content="orgUnit,period\nfkt,202610\n")
    checkpoint_store.abandon_run()

    checkpoint_store.open_run("COM/Respinf")  # same level (fokontany)
    assert "fkt" in (tmp_path / "input" / "external_data.csv").read_text()
    checkpoint_store.abandon_run()

    checkpoint_store.open_run("CSB/Malaria")  # other level: nothing restored
    assert not (tmp_path / "input" / "external_data.csv").exists()
    assert _status(checkpoint_store.progress(), "forecast", "external_data/csb") == "pending"


def test_replacing_a_used_config_resets_only_the_open_run(checkpoint_store):
    _import(checkpoint_store)
    _full_run(checkpoint_store, "ADJ/Malaria")
    checkpoint_store.open_run("COM/Malaria")  # config restored, nothing validated yet

    with pytest.raises(ConfirmationRequiredError) as refused:
        _upload(checkpoint_store)  # ADJ/Malaria already forecast with the current file

    assert refused.value.impact["stale_runs"] == ["ADJ/Malaria"]
    _upload(checkpoint_store, confirm=True)
    assert _status(checkpoint_store.progress(), "forecast", "ADJ/Malaria:post_forecast") == "success"


# --- test mode (TEST_MODE) -----------------------------------------------------------------

def test_test_mode_keeps_checkpoints_in_redis_only(checkpoint_store, tmp_path):
    _pass(checkpoint_store, "import_gee")  # production
    checkpoint_store.set_mode(True)

    _pass(checkpoint_store, "import_pivot_com")

    test_state = checkpoint_store.progress()
    assert test_state["test_mode"] is True
    assert _status(test_state, "data_import", "import_pivot_com") == "success"
    assert _status(test_state, "data_import", "import_gee") == "pending"  # production data is not visible
    assert checkpoint_store._blob.data is not None
    import sqlite3
    rows = sqlite3.connect(tmp_path / "etlhub.db").execute("SELECT item FROM checkpoints").fetchall()
    assert rows == [("import_gee",)]  # nothing written to the SQLite file in test mode


def test_leaving_test_mode_needs_confirm_and_discards_the_test_data_but_its_journal(checkpoint_store):
    _pass(checkpoint_store, "import_gee")
    checkpoint_store.set_mode(True)
    _import(checkpoint_store)
    checkpoint_store.open_run("CSB/Malaria")

    with pytest.raises(ConfirmationRequiredError) as refused:
        checkpoint_store.set_mode(False)
    assert refused.value.impact["open_run"] == "CSB/Malaria"
    assert checkpoint_store.progress()["test_mode"] is True

    assert checkpoint_store.set_mode(False, confirm=True) == {"test_mode": False}
    import sqlite3
    blob = sqlite3.connect(":memory:")
    blob.deserialize(checkpoint_store._blob.data)  # test data stays in Redis only: the journal, nothing else
    assert [blob.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("checkpoints", "forecast_runs")] == [0, 0]
    assert blob.execute("SELECT count(*) FROM pipeline_events").fetchone()[0] > 0
    state = checkpoint_store.progress()
    assert (state["test_mode"], state["run"]) == (False, None)
    assert _status(state, "data_import", "import_gee") == "success"  # production untouched


def test_switching_mode_is_refused_while_a_job_runs(checkpoint_store):
    checkpoint_store.start("import_gee", "busy")

    with pytest.raises(PipelineBlockedError, match="one job at a time"):
        checkpoint_store.set_mode(True)


def test_leaving_an_empty_test_mode_needs_no_confirmation(checkpoint_store):
    checkpoint_store.set_mode(True)

    assert checkpoint_store.set_mode(False) == {"test_mode": False}


# --- journal ------------------------------------------------------------------------------

def _events(store, cycle="202610", **match):
    return [(e["event"], e["item"]) for e in store.journal(cycle) if all(e[k] == v for k, v in match.items())]


def test_the_journal_keeps_every_attempt_and_what_a_relaunch_reset(checkpoint_store, month):
    _import(checkpoint_store)
    checkpoint_store.open_run("ADJ/Malaria")
    _upload(checkpoint_store)
    _upload(checkpoint_store, "external_data")
    for task in ("fetch_disease", "fetch_climate", "fetch_geojson", "validate_inputs"):
        _pass(checkpoint_store, task)
    _pass(checkpoint_store, "fetch_disease", confirm=True)

    journal = checkpoint_store.journal("202610")
    assert [e["event"] for e in journal if e["item"] == "ADJ/Malaria:fetch_disease"] == [
        "launched", "succeeded", "launched", "succeeded"]
    relaunch = [e for e in journal if e["item"] == "ADJ/Malaria:fetch_disease" and e["event"] == "launched"][-1]
    assert relaunch["detail"] == {"confirm": True}
    reset = next(e for e in journal if e["event"] == "reset")
    assert (reset["job_id"], reset["detail"]) == (relaunch["job_id"], {"items": ["ADJ/Malaria:validate_inputs"], "cause": "relaunch"})
    assert ("decided", "approve_imports") in _events(checkpoint_store)
    assert ("uploaded", "config/Malaria") in _events(checkpoint_store)
    assert {e["actor"] for e in journal} == {"worker"}  # no HTTP request in these calls
    assert {e["mode"] for e in journal} == {"production"}


def test_a_refusal_writes_no_event(checkpoint_store, month):
    _pass(checkpoint_store, "import_gee")
    before = checkpoint_store.journal("202610")

    with pytest.raises(PipelineBlockedError):
        checkpoint_store.start("build_analytics", "too_early")
    with pytest.raises(ConfirmationRequiredError):
        checkpoint_store.start("import_gee", "again")

    assert checkpoint_store.journal("202610") == before


def test_events_carry_the_actor_and_the_request_and_flag_it(checkpoint_store, month):
    from etlhub.core.request_context import request_context
    context = {"request_id": "req-1", "actor": "jdoe"}
    token = request_context.set(context)
    try:
        checkpoint_store.start("import_gee", "import_gee_1")
    finally:
        request_context.reset(token)
    checkpoint_store.finish("import_gee_1", "success")  # the worker: no request

    launched, succeeded = checkpoint_store.journal("202610")
    assert (launched["actor"], launched["request_id"]) == ("jdoe", "req-1")
    assert (succeeded["actor"], succeeded["request_id"]) == ("worker", None)
    assert context["pipeline"] is True and context["journal"] is True  # tracked, kept out of the purge


def test_a_job_that_ends_after_its_checkpoint_moved_on_is_journaled_on_its_item(checkpoint_store, month):
    checkpoint_store.start("import_gee", "killed")
    checkpoint_store.release_lock()
    _pass(checkpoint_store, "import_gee")  # in error after the release: no confirmation

    checkpoint_store.finish("killed", "success")  # the killed worker reports late

    assert _events(checkpoint_store, job_id="killed") == [
        ("launched", "import_gee"), ("lock_released", "import_gee"), ("succeeded", "import_gee")]


def test_a_month_change_abandon_is_journaled_in_the_old_cycle(checkpoint_store, month):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    month("202611")
    _pass(checkpoint_store, "import_gee")

    abandoned = next(e for e in checkpoint_store.journal("202610") if e["event"] == "run_abandoned")
    assert (abandoned["actor"], abandoned["detail"]) == ("system", {"couple": "COM/Malaria", "by": "month_change"})


def test_closing_the_cycle_is_journaled_once(checkpoint_store, month):
    _all_runs(checkpoint_store)
    for task in ("build_analytics", "update_key"):
        _pass(checkpoint_store, task)

    assert [e for e, _ in _events(checkpoint_store)].count("cycle_closed") == 1
    assert _events(checkpoint_store)[-1] == ("cycle_closed", None)


def test_the_test_journal_stays_in_redis_and_is_read_with_production(checkpoint_store, month, tmp_path):
    _pass(checkpoint_store, "import_gee")
    checkpoint_store.set_mode(True)
    _pass(checkpoint_store, "import_pivot_com")
    checkpoint_store.set_mode(False, confirm=True)

    journal = checkpoint_store.journal("202610")
    assert [(e["mode"], e["event"], e["item"]) for e in journal] == [
        ("production", "launched", "import_gee"), ("production", "succeeded", "import_gee"),
        ("production", "mode_changed", None),
        ("test", "launched", "import_pivot_com"), ("test", "succeeded", "import_pivot_com"),
        ("production", "mode_changed", None),
    ]
    import sqlite3
    items = sqlite3.connect(tmp_path / "etlhub.db").execute("SELECT DISTINCT item FROM pipeline_events").fetchall()
    assert ("import_pivot_com",) not in items  # never in the SQLite file

    checkpoint_store._blob.delete()  # Redis flushed: production only, no error
    assert {e["mode"] for e in checkpoint_store.journal("202610")} == {"production"}


def test_cycles_lists_every_cycle_with_its_state_and_activity(checkpoint_store, month):
    _all_runs(checkpoint_store)
    for task in ("build_analytics", "update_key"):
        _pass(checkpoint_store, task)  # 202610 complete
    month("202611")
    checkpoint_store.set_mode(True)
    _pass(checkpoint_store, "import_gee")  # 202611: test events only
    checkpoint_store.set_mode(False, confirm=True)
    month("202612")  # the target: no history yet

    cycles = {c["cycle"]: c for c in checkpoint_store.cycles()}

    assert list(cycles) == ["202612", "202611", "202610"]
    assert (cycles["202612"]["target"], cycles["202612"]["events"], cycles["202612"]["last_at"]) == (True, 0, None)
    assert (cycles["202611"]["test_events"], cycles["202611"]["state"]) == (2, "open")
    assert cycles["202611"]["events"] == 0  # mode_changed in and out are not counted
    assert cycles["202611"]["test_state"] is None  # test checkpoints discarded when test mode was left
    assert cycles["202610"]["state"] == "closed" and cycles["202610"]["events"] > 0 and cycles["202610"]["last_at"]



def test_cycles_shows_the_test_state_while_test_mode_has_checkpoints(checkpoint_store, month):
    _pass(checkpoint_store, "import_gee")
    checkpoint_store.set_mode(True)
    _pass(checkpoint_store, "import_pivot_com")

    (cycle,) = checkpoint_store.cycles()

    assert (cycle["state"], cycle["test_state"], cycle["events"], cycle["test_events"]) == ("open", "open", 2, 2)


def test_test_mode_starts_from_the_old_dryrun_once_then_leaves_dryrun_to_env(monkeypatch):
    from etlhub.infrastructure import checkpoint_store as module

    class Redis(dict):
        def set(self, key, value, nx=False):
            if not (nx and key in self):
                self[key] = value

    redis, removed = Redis(), []
    monkeypatch.setattr(module, "get_redis", lambda: redis)
    monkeypatch.setattr(module, "ConfigStore", lambda: type("C", (), {"delete_keys": lambda self, keys: removed.extend(keys) or True})())
    monkeypatch.setattr(module, "dry_run_enabled", lambda: True)  # the pipeline was in test mode through DRYRUN

    assert module.test_mode_enabled() is True
    assert removed == ["DRYRUN"]  # the scripts read DRYRUN from .env again

    monkeypatch.setattr(module, "dry_run_enabled", lambda: False)
    module.write_test_mode(False)
    assert module.test_mode_enabled() is False and removed == ["DRYRUN"]  # TEST_MODE alone from now on


def test_test_mode_and_dryrun_are_independent(checkpoint_store):
    checkpoint_store.mode["dry_run"] = False  # .env: the scripts write to DHIS2

    assert checkpoint_store.set_mode(True) == {"test_mode": True}

    state = checkpoint_store.progress()
    assert (state["test_mode"], state["dry_run"]) == (True, False)
