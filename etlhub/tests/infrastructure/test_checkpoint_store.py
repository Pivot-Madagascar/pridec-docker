import itertools

import pytest

from etlhub.domain.exceptions import ConfirmationRequiredError, PipelineBlockedError, ValidationError
from etlhub.domain.pipeline import COUPLES, PIPELINE, check_forecast_start, run_items

_ids = itertools.count()


def _pass(store, task, confirm=False):
    job_id = f"{task}_{next(_ids)}"
    store.start(task, job_id, confirm)
    store.finish(job_id, "success")
    return job_id


def _import(store):
    for task in ("import_pivot_csb", "import_gee", "import_pivot_com", "build_analytics"):
        _pass(store, task)


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
    """Opens the run and passes everything up to approve (excluded). config only for the disease's first run."""
    store.open_run(couple)
    if _status(store.progress(), "forecast", f"config/{couple.split('/')[1]}") != "success":
        _upload(store)
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

def test_the_target_pipeline_has_three_steps_and_69_forecast_items():
    assert list(PIPELINE) == ["data_import", "forecast", "system_update"]
    assert len(PIPELINE["forecast"]) == 69  # 3 configs (one per disease) + 6 x 7 + 3 x 8
    assert len(run_items("COM/Malaria")) == 7
    assert "CSB/Malaria:calc_orgunit_alerts" in run_items("CSB/Malaria")


def test_a_new_cycle_starts_at_data_import(checkpoint_store):
    state = checkpoint_store.progress()

    assert state["current_step"] == "data_import"
    assert state["cycle_state"] == "open"
    assert [s["accessible"] for s in state["steps"]] == [True, False, False]
    assert state["run"] is None and state["lock"] is None


# --- R2, R3, R4 ---------------------------------------------------------------------------

def test_imports_run_in_any_order_and_build_analytics_waits_for_the_three(checkpoint_store):
    _pass(checkpoint_store, "import_pivot_com")
    with pytest.raises(PipelineBlockedError, match="data_import/import_gee"):
        checkpoint_store.start("build_analytics", "early")

    for task in ("import_pivot_csb", "import_gee", "build_analytics"):
        _pass(checkpoint_store, task)

    assert _step(checkpoint_store.progress(), "data_import")["done"] is True


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
    for task in ("fetch_disease", "fetch_climate", "fetch_geojson", "validate_inputs", "forecast"):
        _pass(checkpoint_store, task)

    with pytest.raises(PipelineBlockedError, match="CSB/Malaria:calc_orgunit_alerts"):
        checkpoint_store.decide("approve")


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


def test_external_data_is_optional_and_recorded_on_the_run(checkpoint_store):
    _import(checkpoint_store)
    _prepare(checkpoint_store, "ADJ/Respinf")
    assert checkpoint_store.progress()["run"]["external_data"] == "none"

    with pytest.raises(ConfirmationRequiredError):
        _upload(checkpoint_store, "external_data")
    _upload(checkpoint_store, "external_data", confirm=True)

    state = checkpoint_store.progress()
    assert state["run"]["external_data"] == "uploaded"
    assert _status(state, "forecast", "ADJ/Respinf:validate_inputs") == "pending"
    assert _status(state, "forecast", "ADJ/Respinf:forecast") == "pending"


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


def test_build_analytics_fills_its_three_slots_in_order(checkpoint_store):
    _all_runs(checkpoint_store)

    first = _pass(checkpoint_store, "build_analytics")
    with pytest.raises(ConfirmationRequiredError):  # after_alerts not launchable yet: a relaunch of the first
        checkpoint_store.start("build_analytics", "too_early")
    _pass(checkpoint_store, "calc_csb_alerts")
    second = _pass(checkpoint_store, "build_analytics")

    update = {i["item"]: i["job_id"] for i in _step(checkpoint_store.progress(), "system_update")["items"]}
    assert (update["build_analytics"], update["build_analytics_after_alerts"]) == (first, second)
    with pytest.raises(ConfirmationRequiredError):  # all three in success: a relaunch of the last
        checkpoint_store.start("build_analytics", "third")


def test_the_whole_cycle_completes_then_closes_until_next_month(checkpoint_store, month):
    _all_runs(checkpoint_store)
    for task in ("build_analytics", "calc_csb_alerts", "build_analytics", "update_key"):
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


@pytest.mark.parametrize("forecast_start, cycle, ok", [
    ("202610", "202610", True),
    (202610, "202610", True),
    (None, "202610", True),        # absent: validate_inputs takes the current month
    (None, "202609", False),       # absent, but the cycle started last month
    ("202601", "202610", False),
])
def test_config_forecast_start_must_match_the_cycle(forecast_start, cycle, ok):
    if ok:
        check_forecast_start(forecast_start, cycle, "202610")
    else:
        with pytest.raises(ValidationError):
            check_forecast_start(forecast_start, cycle, "202610")



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

    run = checkpoint_store.open_run("COM/Respinf")  # same level (fokontany)
    assert run["external_data"] == "uploaded"
    assert "fkt" in (tmp_path / "input" / "external_data.csv").read_text()
    checkpoint_store.abandon_run()

    assert checkpoint_store.open_run("CSB/Malaria")["external_data"] == "none"  # other level


def test_replacing_a_used_config_resets_only_the_open_run(checkpoint_store):
    _import(checkpoint_store)
    _full_run(checkpoint_store, "ADJ/Malaria")
    checkpoint_store.open_run("COM/Malaria")  # config restored, nothing validated yet

    with pytest.raises(ConfirmationRequiredError) as refused:
        _upload(checkpoint_store)  # ADJ/Malaria already forecast with the current file

    assert refused.value.impact["stale_runs"] == ["ADJ/Malaria"]
    _upload(checkpoint_store, confirm=True)
    assert _status(checkpoint_store.progress(), "forecast", "ADJ/Malaria:post_forecast") == "success"


# --- test mode (DRYRUN) -----------------------------------------------------------------

def test_test_mode_keeps_checkpoints_in_redis_only(checkpoint_store, tmp_path):
    _pass(checkpoint_store, "import_gee")  # production
    checkpoint_store.set_mode(True)

    _pass(checkpoint_store, "import_pivot_com")

    test_state = checkpoint_store.progress()
    assert test_state["dry_run"] is True
    assert _status(test_state, "data_import", "import_pivot_com") == "success"
    assert _status(test_state, "data_import", "import_gee") == "pending"  # production data is not visible
    assert checkpoint_store._blob.data is not None
    import sqlite3
    rows = sqlite3.connect(tmp_path / "etlhub.db").execute("SELECT item FROM checkpoints").fetchall()
    assert rows == [("import_gee",)]  # nothing written to the SQLite file in test mode


def test_leaving_test_mode_needs_confirm_and_discards_the_test_data(checkpoint_store):
    _pass(checkpoint_store, "import_gee")
    checkpoint_store.set_mode(True)
    _import(checkpoint_store)
    checkpoint_store.open_run("CSB/Malaria")

    with pytest.raises(ConfirmationRequiredError) as refused:
        checkpoint_store.set_mode(False)
    assert refused.value.impact["open_run"] == "CSB/Malaria"
    assert checkpoint_store.progress()["dry_run"] is True

    assert checkpoint_store.set_mode(False, confirm=True) == {"dry_run": False}
    assert checkpoint_store._blob.data is None
    state = checkpoint_store.progress()
    assert (state["dry_run"], state["run"]) == (False, None)
    assert _status(state, "data_import", "import_gee") == "success"  # production untouched


def test_switching_mode_is_refused_while_a_job_runs(checkpoint_store):
    checkpoint_store.start("import_gee", "busy")

    with pytest.raises(PipelineBlockedError, match="one job at a time"):
        checkpoint_store.set_mode(True)


def test_leaving_an_empty_test_mode_needs_no_confirmation(checkpoint_store):
    checkpoint_store.set_mode(True)

    assert checkpoint_store.set_mode(False) == {"dry_run": False}
