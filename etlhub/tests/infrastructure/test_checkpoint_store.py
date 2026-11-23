import itertools
import re
import shutil
import sqlite3
from contextlib import closing

import pytest

from etlhub.infrastructure.checkpoint_store import PASS_CONFIG
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
    with pytest.raises(PipelineBlockedError, match="No active pass"):
        checkpoint_store.open_run("COM/Malaria")
    _pass(checkpoint_store, "import_gee")  # starts the pass
    with pytest.raises(PipelineBlockedError, match="data_import done first"):
        checkpoint_store.open_run("COM/Malaria")
    for task in ("import_pivot_csb", "import_pivot_com"):
        _pass(checkpoint_store, task)
    checkpoint_store.decide_imports("approve")
    _pass(checkpoint_store, "build_analytics")

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


def test_opening_a_run_empties_input_and_output_but_not_the_pass_folders(checkpoint_store, month, tmp_path):
    _import(checkpoint_store)
    (tmp_path / "input" / "disease_data.json").write_text("{}")
    (tmp_path / "output" / "forecast.json").write_text("{}")

    checkpoint_store.open_run("COM/Malaria")

    assert [f.name for f in (tmp_path / "input").iterdir()] == ["202610"]  # input/<cycle>/<pass>/ stays
    assert [f.name for f in (tmp_path / "output").iterdir()] == ["202610"]


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

    pass_id = checkpoint_store.progress()["pass"]["id"]
    assert checkpoint_store.report(pass_id, "COM/Malaria").read_text() == "<p>COM Malaria</p>"
    assert checkpoint_store.report(None, "COM/Malaria") == checkpoint_store.report(pass_id, "COM/Malaria")
    assert checkpoint_store.report(pass_id, "ADJ/Malaria") is None


def test_abandoning_a_run_resets_its_items(checkpoint_store):
    _import(checkpoint_store)
    _prepare(checkpoint_store, "ADJ/Malaria")

    assert checkpoint_store.abandon_run() == "ADJ/Malaria"

    state = checkpoint_store.progress()
    assert state["run"] is None
    assert _status(state, "forecast", "ADJ/Malaria:forecast") == "pending"
    assert state["pass"]["state"] == "active"  # the pass goes on
    abandoned = [e for e in checkpoint_store.journal(state["pass"]["id"]) if e["event"] == "run_abandoned"]
    assert abandoned[-1]["detail"] == {"couple": "ADJ/Malaria", "by": "manual"}
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


def test_a_complete_pass_is_frozen_and_its_month_is_redone_in_a_new_pass_with_confirm(checkpoint_store, month):
    _all_runs(checkpoint_store)
    for task in ("build_analytics", "update_key"):
        _pass(checkpoint_store, task)
    first = checkpoint_store.progress()
    assert (first["current_step"], first["pass"]["state"]) == (None, "complete")

    with pytest.raises(ConfirmationRequiredError, match="202610 is complete") as refused:
        checkpoint_store.start("import_gee", "again")
    assert refused.value.impact == {"cycle": "202610", "complete_pass": first["pass"]["id"]}
    _pass(checkpoint_store, "import_gee", confirm=True)

    second = checkpoint_store.progress()
    assert second["pass"]["id"] != first["pass"]["id"] and second["pass"]["state"] == "active"
    assert second["current_step"] == "data_import"  # from zero
    assert checkpoint_store.progress(first["pass"]["id"])["current_step"] is None  # untouched
    started = checkpoint_store.journal(second["pass"]["id"])[0]
    assert (started["event"], started["detail"]) == ("pass_started", {"cause": "redo", "parent_ou": "ou_parent", "log_level": "INFO", "dry_run": False, "dhis_url": "https://dhis2.test"})
    assert checkpoint_store.journal(first["pass"]["id"])[-1]["event"] == "cycle_closed"  # nothing after it


def test_a_month_change_leaves_the_active_pass_active_on_its_month(checkpoint_store, month):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    old = checkpoint_store.progress()["pass"]
    month("202611")

    state = checkpoint_store.progress()  # the first request of the month: nothing changes (2026-11-20, pass-config.md)
    assert (state["cycle"], state["pass"]["id"], state["pass"]["state"], state["run"]["couple"]) == (
        "202610", old["id"], "active", "COM/Malaria")
    assert all(e["event"] != "paused" for e in checkpoint_store.journal(old["id"]))

    checkpoint_store.pause()  # only the user stops it; 202611 then starts its own pass
    _pass(checkpoint_store, "import_gee")
    assert checkpoint_store.progress()["pass"]["cycle"] == "202611"


def test_a_chosen_month_takes_the_next_pass_and_is_not_paused_by_the_calendar(checkpoint_store, month):
    with pytest.raises(PipelineBlockedError, match="future"):
        checkpoint_store.set_cycle("202611")

    assert checkpoint_store.set_cycle("202609") == {"cycle": "202609"}
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    assert checkpoint_store.progress()["pass"]["cycle"] == "202609"
    with pytest.raises(PipelineBlockedError, match=r"\(202609\) is active: pause or abandon it first"):
        checkpoint_store.set_cycle(None)

    month("202611")  # a chosen month does not follow the calendar: its pass stays active
    assert checkpoint_store.progress()["run"]["couple"] == "COM/Malaria"


def test_pause_then_resume_from_the_journal_continues_where_it_stopped(checkpoint_store, month):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    _pass(checkpoint_store, "fetch_disease")
    p = checkpoint_store.pause()

    assert checkpoint_store.progress()["pass"]["state"] == "paused"
    with pytest.raises(PipelineBlockedError, match=f"Pass {p['id']} of cycle 202610 is paused"):
        checkpoint_store.start("fetch_climate", "while_paused")

    checkpoint_store.resume(p["id"])
    state = checkpoint_store.progress()
    assert (state["pass"]["state"], state["run"]["couple"]) == ("active", "COM/Malaria")
    assert _status(state, "forecast", "COM/Malaria:fetch_disease") == "success"  # nothing redone
    _pass(checkpoint_store, "fetch_climate")
    assert [e["event"] for e in checkpoint_store.journal(p["id"]) if e["event"] in ("paused", "resumed")] == [
        "paused", "resumed"]


def test_starting_a_pass_creates_it_at_once_with_its_folders_and_carried_items(checkpoint_store, month, tmp_path):
    params = {"import_gee": {"p": 1}, "import_pivot_com": {"p": 2}, "import_pivot_csb": {"p": 3}}
    for task in ("import_gee", "import_pivot_com", "import_pivot_csb"):
        job_id = f"{task}_{next(_ids)}"
        checkpoint_store.start(task, job_id, carry_over=params)
        checkpoint_store.finish(job_id, "success")
    first = checkpoint_store.pause()

    with pytest.raises(ConfirmationRequiredError, match=f"Pass {first['id']} of cycle 202610 is paused"):
        checkpoint_store.start_pass(carry_over=params)
    p = checkpoint_store.start_pass(confirm=True, carry_over=params)

    state = checkpoint_store.progress()
    assert (state["pass"]["id"], state["pass"]["state"]) == (p["id"], "active")  # the Dashboard shows the new pass
    assert _status(state, "data_import", "import_gee") == "success"  # carried, nothing launched
    assert (tmp_path / "input" / "202610" / p["id"]).is_dir() and (tmp_path / "output" / "202610" / p["id"]).is_dir()
    with pytest.raises(PipelineBlockedError, match=f"Pass {p['id']} \\(202610\\) is active"):
        checkpoint_store.start_pass(confirm=True)


def test_pause_is_refused_while_a_job_runs(checkpoint_store):
    checkpoint_store.start("import_gee", "busy")

    with pytest.raises(PipelineBlockedError, match="one job at a time"):
        checkpoint_store.pause()


def test_a_new_pass_after_a_pause_needs_confirm_takes_its_uploads_and_abandon_keeps_only_reports(checkpoint_store, month, tmp_path):
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    _upload(checkpoint_store, content='{"m": 1}')
    _pass(checkpoint_store, "fetch_disease")
    (tmp_path / "input" / "disease_data.json").write_text("fetched")
    (tmp_path / "output" / "forecast.json").write_text("{}")
    first = checkpoint_store.pause()
    first_in, first_out = (tmp_path / d / "202610" / first["id"] for d in ("input", "output"))
    assert (first_in / "disease_data.json").read_text() == "fetched"  # the working files go with the pass

    with pytest.raises(ConfirmationRequiredError, match=f"Pass {first['id']} of cycle 202610 is paused") as refused:
        checkpoint_store.start("import_gee", "new")
    assert refused.value.impact == {"cycle": "202610", "paused_pass": first["id"]}
    _pass(checkpoint_store, "import_gee", confirm=True)

    second = checkpoint_store.progress()
    assert second["pass"]["id"] != first["id"]
    assert checkpoint_store.progress(first["id"])["pass"]["state"] == "paused"  # to resume from the Journal
    assert _status(second, "forecast", "config/Malaria") == "success"  # carried from the paused pass
    assert (tmp_path / "input" / "202610" / second["pass"]["id"] / "config_Malaria.json").read_text() == '{"m": 1}'
    assert not (tmp_path / "input" / "disease_data.json").exists()  # input/ is the new pass's now

    (first_out / "report_ADJ_Malaria.html").write_text("report")
    checkpoint_store.abandon(first["id"])
    assert not first_in.exists()
    assert [f.name for f in first_out.iterdir()] == ["report_ADJ_Malaria.html"]


def test_two_months_in_turn_one_active_pass_at_a_time(checkpoint_store, month, tmp_path):
    checkpoint_store.set_cycle("202609")
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")
    _upload(checkpoint_store, content='{"m": "09"}')
    _pass(checkpoint_store, "fetch_disease")
    first = checkpoint_store.pause()
    checkpoint_store.set_cycle("202610")
    _import(checkpoint_store)
    checkpoint_store.open_run("ADJ/Malaria")  # empties input/

    with pytest.raises(PipelineBlockedError, match=r"\(202610\) is active: pause or abandon it first"):
        checkpoint_store.resume(first["id"])
    checkpoint_store.pause()
    checkpoint_store.resume(first["id"])

    state = checkpoint_store.progress()
    assert (state["cycle"], state["run"]["couple"]) == ("202609", "COM/Malaria")
    # Another run emptied input/ meanwhile: the pass saved its files when paused, nothing is fetched again
    assert _status(state, "forecast", "COM/Malaria:fetch_disease") == "success"
    assert _status(state, "forecast", "config/Malaria") == "success"
    assert (tmp_path / "input" / "config.json").read_text() == '{"m": "09"}'


def test_an_abandoned_pass_cannot_be_resumed_and_its_month_starts_again(checkpoint_store, month):
    _import(checkpoint_store)
    checkpoint_store.open_run("CSB/Malaria")
    p = checkpoint_store.pause()

    checkpoint_store.abandon(p["id"])  # a paused pass, from the journal

    with pytest.raises(PipelineBlockedError, match="is abandoned: it cannot be resumed"):
        checkpoint_store.resume(p["id"])
    assert [e["event"] for e in checkpoint_store.journal(p["id"])][-2:] == ["run_abandoned", "abandoned"]
    assert checkpoint_store.progress(p["id"])["run"] is None
    _pass(checkpoint_store, "import_gee")  # no confirmation: the month was not complete
    assert checkpoint_store.progress()["pass"]["id"] != p["id"]


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


# --- test mode: the mode of the request or job served (the user's) ---------------------------------

def test_test_mode_keeps_checkpoints_in_redis_only(checkpoint_store, tmp_path):
    _pass(checkpoint_store, "import_gee")  # production
    checkpoint_store.mode["test_mode"] = True

    _pass(checkpoint_store, "import_pivot_com")

    test_state = checkpoint_store.progress()
    assert test_state["test_mode"] is True
    assert _status(test_state, "data_import", "import_pivot_com") == "success"
    assert _status(test_state, "data_import", "import_gee") == "pending"  # production data is not visible
    assert checkpoint_store._blob.data is not None
    rows = sqlite3.connect(tmp_path / "etlhub.db").execute("SELECT item FROM checkpoints").fetchall()
    assert rows == [("import_gee",)]  # nothing written to the SQLite file in test mode


def test_each_mode_keeps_its_active_pass_a_switch_changes_nothing_shared(checkpoint_store):
    _pass(checkpoint_store, "import_gee")
    production_pass = checkpoint_store.progress()["pass"]
    checkpoint_store.mode["test_mode"] = True
    _import(checkpoint_store)
    checkpoint_store.open_run("CSB/Malaria")
    test_pass = checkpoint_store.progress()["pass"]

    checkpoint_store.mode["test_mode"] = False  # another user, or the same one switching: nothing is paused

    state = checkpoint_store.progress()
    assert (state["pass"]["id"], state["pass"]["state"], state["run"]) == (production_pass["id"], "active", None)
    with pytest.raises(PipelineBlockedError, match=f"No pass {test_pass['id']} in production mode"):
        checkpoint_store.resume(test_pass["id"])
    checkpoint_store.mode["test_mode"] = True
    state = checkpoint_store.progress()
    assert (state["pass"]["id"], state["pass"]["state"], state["run"]["couple"]) == (test_pass["id"], "active", "CSB/Malaria")


def test_leaving_a_mode_without_active_pass_asks_nothing(checkpoint_store):
    assert checkpoint_store.leave_mode(None) is None


def test_leaving_a_mode_mid_pass_asks_to_pause_or_abandon_it(checkpoint_store):
    checkpoint_store.mode["test_mode"] = True
    _import(checkpoint_store)
    p = checkpoint_store.progress()["pass"]

    with pytest.raises(ConfirmationRequiredError) as asked:
        checkpoint_store.leave_mode(None)

    assert asked.value.impact == {"pass_id": p["id"], "cycle": p["cycle"], "mode": "test", "to": "production",
                                  "actions": ["pause", "abandon"]}
    assert checkpoint_store.progress()["pass"]["state"] == "active"  # nothing done before the choice


@pytest.mark.parametrize("action, state", [("pause", "paused"), ("abandon", "abandoned")])
def test_the_pass_left_by_a_mode_change_says_so_in_its_journal(checkpoint_store, action, state):
    checkpoint_store.mode["test_mode"] = True
    _import(checkpoint_store)
    p = checkpoint_store.progress()["pass"]

    assert checkpoint_store.leave_mode(action)["state"] == state

    last = checkpoint_store.journal(p["id"])[-1]
    assert (last["event"], last["detail"]) == (state, {
        "cause": "mode_change", "reason": "Mode changed manually by the user: from test to production"})
    assert checkpoint_store.leave_mode(None) is None  # no active pass left in test mode


def test_a_pass_cannot_be_left_while_a_job_runs(checkpoint_store):
    checkpoint_store.start("import_gee", "import_gee_00000001")

    with pytest.raises(PipelineBlockedError, match="one job at a time"):
        checkpoint_store.leave_mode("pause")
    assert checkpoint_store.progress()["pass"]["state"] == "active"


def test_one_job_at_a_time_across_both_modes_the_other_modes_job_unnamed(checkpoint_store):
    checkpoint_store.start("import_gee", "import_gee_00000001")  # production
    checkpoint_store.mode["test_mode"] = True

    with pytest.raises(PipelineBlockedError, match="^A job of the other mode is running since .*: one job at a time"):
        checkpoint_store.start("import_pivot_com", "import_pivot_com_00000002")
    assert checkpoint_store.progress()["lock"] == {"job_id": None, "task": "a job of the other mode",
                                                   "acquired_at": checkpoint_store.progress()["lock"]["acquired_at"]}
    checkpoint_store.mode["test_mode"] = False
    assert checkpoint_store.progress()["lock"]["job_id"] == "import_gee_00000001"
    checkpoint_store.finish("import_gee_00000001", "success")

    checkpoint_store.mode["test_mode"] = True
    checkpoint_store.start("import_pivot_com", "import_pivot_com_00000002")  # free again
    checkpoint_store.mode["test_mode"] = False
    with pytest.raises(PipelineBlockedError, match="^A job of the other mode"):
        checkpoint_store.start("import_gee", "import_gee_00000003")


def test_a_killed_job_is_released_from_either_mode_and_journaled_in_its_own(checkpoint_store):
    checkpoint_store.mode["test_mode"] = True
    checkpoint_store.start("import_gee", "import_gee_0000000a")
    test_pass = checkpoint_store.progress()["pass"]["id"]
    checkpoint_store.mode["test_mode"] = False

    assert checkpoint_store.release_lock("import_gee_0000000a") == "import_gee_0000000a"

    assert checkpoint_store.progress()["lock"] is None
    assert checkpoint_store.journal(test_pass) == []  # production reads nothing of it
    checkpoint_store.mode["test_mode"] = True
    assert checkpoint_store.journal(test_pass)[-1]["event"] == "lock_released"
    assert _status(checkpoint_store.progress(), "data_import", "import_gee") == "error"


def test_each_mode_works_in_its_own_folders_and_an_old_test_pass_folder_moves_on_use(checkpoint_store, tmp_path):
    _import(checkpoint_store)  # a production pass: it emptied ./input when it started
    (tmp_path / "input" / "climate_data.json").write_text("production")
    checkpoint_store.mode["test_mode"] = True
    _import(checkpoint_store)
    test_pass = checkpoint_store.progress()["pass"]
    for root in ("input", "output"):  # a pass of before test/: its folders are still in ./input, ./output
        shutil.rmtree(tmp_path / "test" / root / test_pass["cycle"] / test_pass["id"], ignore_errors=True)
    legacy = tmp_path / "input" / test_pass["cycle"] / test_pass["id"]
    legacy.mkdir(parents=True)
    (legacy / "config_Malaria.json").write_text("{}")  # a kept upload of that pass

    checkpoint_store.open_run("CSB/Malaria")  # empties the working files of the mode's folders
    assert (tmp_path / "input" / "climate_data.json").read_text() == "production"  # production untouched

    checkpoint_store.pause()  # saves the test pass's work into its folder: the old one moves first
    assert not legacy.exists()
    assert (tmp_path / "test" / "input" / test_pass["cycle"] / test_pass["id"] / "config_Malaria.json").exists()


# --- journal ------------------------------------------------------------------------------

def _journal(store):
    """The journal of the pass the Dashboard shows."""
    return store.journal(store.progress()["pass"]["id"])


def _events(store, **match):
    return [(e["event"], e["item"]) for e in _journal(store) if all(e[k] == v for k, v in match.items())]


def test_the_journal_keeps_every_attempt_and_what_a_relaunch_reset(checkpoint_store, month):
    _import(checkpoint_store)
    checkpoint_store.open_run("ADJ/Malaria")
    _upload(checkpoint_store)
    _upload(checkpoint_store, "external_data")
    for task in ("fetch_disease", "fetch_climate", "fetch_geojson", "validate_inputs"):
        _pass(checkpoint_store, task)
    _pass(checkpoint_store, "fetch_disease", confirm=True)

    journal = _journal(checkpoint_store)
    assert [e["event"] for e in journal if e["item"] == "ADJ/Malaria:fetch_disease"] == [
        "launched", "succeeded", "launched", "succeeded"]
    relaunch = [e for e in journal if e["item"] == "ADJ/Malaria:fetch_disease" and e["event"] == "launched"][-1]
    assert relaunch["detail"] == {"confirm": True, "dry_run": False}  # production: DRYRUN = TEST MODE
    reset = next(e for e in journal if e["event"] == "reset")
    assert (reset["job_id"], reset["detail"]) == (relaunch["job_id"], {"items": ["ADJ/Malaria:validate_inputs"], "cause": "relaunch"})
    assert ("decided", "approve_imports") in _events(checkpoint_store)
    assert ("uploaded", "config/Malaria") in _events(checkpoint_store)
    assert {e["actor"] for e in journal} == {"worker"}  # no HTTP request in these calls
    assert {(e["mode"], e["cycle"]) for e in journal} == {("production", "202610")}


def _check(store, task="import_pivot_com", params="P", started_at=None):
    from datetime import datetime
    started_at = started_at or datetime.now().isoformat(timespec="microseconds")
    section = {"task": task, "params": params, "section": {"task": task}, "last_analytics": "b"}
    return store.record_availability_check("availability_checked", {"checked": [task]}, [section], started_at)


def test_an_availability_check_is_journaled_in_the_shown_pass_even_while_a_job_runs(checkpoint_store, month):
    _check(checkpoint_store)  # no pass yet: in no journal
    _pass(checkpoint_store, "import_gee")
    checkpoint_store.start("import_pivot_csb", "running")

    meta = _check(checkpoint_store)  # a read: no lock, no checkpoint

    journal = _journal(checkpoint_store)
    assert [e["detail"] for e in journal if e["event"] == "availability_checked"] == [{"checked": ["import_pivot_com"]}]
    assert meta["pass_id"] == checkpoint_store.progress()["pass"]["id"]
    assert _status(checkpoint_store.progress(), "data_import", "import_pivot_csb") == "running"


def test_a_stored_check_holds_in_its_cycle_until_its_import_is_launched_or_30_days_pass(checkpoint_store, month):
    from datetime import datetime, timedelta
    _check(checkpoint_store, "import_gee")
    _check(checkpoint_store, "import_pivot_csb", started_at=(datetime.now() - timedelta(days=31)).isoformat())
    _check(checkpoint_store)
    asked = {"import_gee": "P", "import_pivot_com": "P", "import_pivot_csb": "P"}

    assert set(checkpoint_store.reusable_availability(asked)) == {"import_gee", "import_pivot_com"}  # csb: too old
    assert checkpoint_store.reusable_availability({"import_gee": "other params"}) == {}

    _pass(checkpoint_store, "import_gee")  # a new pass of the same cycle, launched after the check
    assert set(checkpoint_store.reusable_availability(asked)) == {"import_pivot_com"}

    checkpoint_store.pause()
    month("202611")
    assert checkpoint_store.reusable_availability(asked) == {}  # another cycle


def test_a_successful_build_analytics_invalidates_every_stored_check(checkpoint_store, month):
    _imports_approved(checkpoint_store)
    asked = {"import_gee": "P", "import_pivot_com": "P", "import_pivot_csb": "P"}
    for task in asked:
        _check(checkpoint_store, task)

    checkpoint_store.start("build_analytics", "b1")
    assert set(checkpoint_store.reusable_availability(asked)) == set(asked)  # still building: the analytics are as checked
    checkpoint_store.finish("b1", "success")
    assert checkpoint_store.reusable_availability(asked) == {}  # rebuilt: every section's analytics may have changed


def test_every_launch_journals_the_mode_s_dryrun_and_an_import_its_parameters(checkpoint_store, month):
    _pass(checkpoint_store, "import_gee")
    _pass(checkpoint_store, "import_pivot_com")

    checkpoint_store.start("import_pivot_csb", "csb_1", carry_over={"import_pivot_csb": {"task": "import_pivot_csb"}})

    launched = [e for e in _journal(checkpoint_store) if e["event"] == "launched"]
    assert [(e["item"], e["detail"]) for e in launched] == [  # production: DRYRUN = TEST MODE = false
        ("import_gee", {"dry_run": False}), ("import_pivot_com", {"dry_run": False}),
        ("import_pivot_csb", {"dry_run": False, "params": {"task": "import_pivot_csb"}})]  # an import's parameters


def test_a_refusal_writes_no_event(checkpoint_store, month):
    _pass(checkpoint_store, "import_gee")
    before = _journal(checkpoint_store)

    with pytest.raises(PipelineBlockedError):
        checkpoint_store.start("build_analytics", "too_early")
    with pytest.raises(ConfirmationRequiredError):
        checkpoint_store.start("import_gee", "again")

    assert _journal(checkpoint_store) == before


def test_events_carry_the_actor_and_the_request_and_flag_it(checkpoint_store, month):
    from etlhub.core.request_context import request_context
    context = {"request_id": "req-1", "actor": "jdoe"}
    token = request_context.set(context)
    try:
        checkpoint_store.start("import_gee", "import_gee_1")
    finally:
        request_context.reset(token)
    checkpoint_store.finish("import_gee_1", "success")  # the worker: no request

    started, launched, succeeded = _journal(checkpoint_store)
    assert checkpoint_store.progress()["pass"]["started_by"] == "jdoe"
    assert (started["actor"], launched["actor"], launched["request_id"]) == ("jdoe", "jdoe", "req-1")
    assert (succeeded["actor"], succeeded["request_id"]) == ("worker", None)
    assert context["pipeline"] is True and context["journal"] is True  # tracked, kept out of the purge


def test_each_action_keeps_its_own_user_whoever_started_the_pass(checkpoint_store, month):
    from etlhub.core.request_context import request_context

    def as_user(name, action):
        token = request_context.set({"request_id": f"req-{name}", "actor": name})
        try:
            return action()
        finally:
            request_context.reset(token)

    as_user("alice", lambda: checkpoint_store.start("import_gee", "a"))
    checkpoint_store.finish("a", "success")
    as_user("bob", lambda: checkpoint_store.start("import_pivot_com", "b"))
    checkpoint_store.finish("b", "success")
    p = as_user("bob", checkpoint_store.pause)
    as_user("carol", lambda: checkpoint_store.resume(p["id"]))

    assert p["started_by"] == "alice"
    assert [(e["event"], e["actor"]) for e in checkpoint_store.journal(p["id"]) if e["event"] != "succeeded"] == [
        ("pass_started", "alice"), ("launched", "alice"), ("launched", "bob"), ("paused", "bob"), ("resumed", "carol")]


def test_a_job_that_ends_after_its_checkpoint_moved_on_is_journaled_on_its_item(checkpoint_store, month):
    checkpoint_store.start("import_gee", "killed")
    checkpoint_store.release_lock()
    _pass(checkpoint_store, "import_gee")  # in error after the release: no confirmation

    checkpoint_store.finish("killed", "success")  # the killed worker reports late

    assert _events(checkpoint_store, job_id="killed") == [
        ("launched", "import_gee"), ("lock_released", "import_gee"), ("succeeded", "import_gee")]


def test_closing_the_cycle_is_journaled_once(checkpoint_store, month):
    _all_runs(checkpoint_store)
    for task in ("build_analytics", "update_key"):
        _pass(checkpoint_store, task)

    assert [e for e, _ in _events(checkpoint_store)].count("cycle_closed") == 1
    assert _events(checkpoint_store)[-1] == ("cycle_closed", None)


def test_the_test_journal_stays_in_redis_and_each_mode_reads_only_its_own(checkpoint_store, month, tmp_path):
    _pass(checkpoint_store, "import_gee")
    production = checkpoint_store.progress()["pass"]["id"]
    checkpoint_store.mode["test_mode"] = True
    _pass(checkpoint_store, "import_pivot_com")
    test = checkpoint_store.progress()["pass"]["id"]
    checkpoint_store.mode["test_mode"] = False

    assert [(e["mode"], e["event"]) for e in checkpoint_store.journal(production)] == [
        ("production", "pass_started"), ("production", "launched"), ("production", "succeeded")]
    assert checkpoint_store.journal(test) == []  # a test pass is never readable in production
    items = sqlite3.connect(tmp_path / "etlhub.db").execute("SELECT DISTINCT item FROM pipeline_events").fetchall()
    assert ("import_pivot_com",) not in items  # never in the SQLite file

    checkpoint_store.mode["test_mode"] = True
    assert [(e["mode"], e["event"], e["item"]) for e in checkpoint_store.journal(test)] == [
        ("test", "pass_started", None), ("test", "launched", "import_pivot_com"),
        ("test", "succeeded", "import_pivot_com")]
    assert checkpoint_store.journal(production) == []  # nor a production pass in test mode

    checkpoint_store._blob.delete()  # Redis flushed: the test pass is gone, no error
    assert checkpoint_store.journal(test) == []


def test_a_mode_knows_only_the_jobs_its_own_pipeline_launched(checkpoint_store):
    _pass(checkpoint_store, "import_gee")
    production_job = checkpoint_store.progress()["steps"][0]["items"][0]["job_id"]
    checkpoint_store.mode["test_mode"] = True
    _pass(checkpoint_store, "import_pivot_com")
    test_job = next(i["job_id"] for i in checkpoint_store.progress()["steps"][0]["items"] if i["item"] == "import_pivot_com")

    assert checkpoint_store.current_mode() == "test"
    assert (checkpoint_store.has_job(test_job), checkpoint_store.has_job(production_job)) == (True, False)
    checkpoint_store.mode["test_mode"] = False
    assert checkpoint_store.current_mode() == "production"
    assert (checkpoint_store.has_job(production_job), checkpoint_store.has_job(test_job)) == (True, False)
    assert checkpoint_store.has_job("import_gee_00000000") is False


def test_cycles_lists_months_with_the_passes_of_the_current_mode_only(checkpoint_store, month):
    _all_runs(checkpoint_store)
    for task in ("build_analytics", "update_key"):
        _pass(checkpoint_store, task)  # 202610: a complete pass
    _pass(checkpoint_store, "import_gee", confirm=True)  # 202610 again: a second pass
    checkpoint_store.pause()
    month("202611")
    checkpoint_store.mode["test_mode"] = True
    _pass(checkpoint_store, "import_gee")  # 202611: a test pass
    checkpoint_store.mode["test_mode"] = False
    month("202612")  # the target: no pass yet

    cycles = {c["cycle"]: c for c in checkpoint_store.cycles()}

    assert list(cycles) == ["202612", "202610"]  # 202611 has a test pass only: not listed in production
    assert (cycles["202612"]["target"], cycles["202612"]["passes"]) == (True, [])
    second, first = cycles["202610"]["passes"]  # newest first
    assert (second["state"], first["state"], first["started_by"]) == ("paused", "complete", "worker")
    assert first["events"] > second["events"] > 0 and first["last_at"]
    assert {p["mode"] for c in cycles.values() for p in c["passes"]} == {"production"}

    checkpoint_store.mode["test_mode"] = True
    cycles = {c["cycle"]: c for c in checkpoint_store.cycles()}
    (test,) = cycles["202611"]["passes"]
    assert (test["mode"], test["state"], test["events"]) == ("test", "active", 3)  # started, launched, succeeded
    assert [p for c in cycles.values() for p in c["passes"]] == [test]  # no production pass in test mode


_LEGACY_SCHEMA = """
CREATE TABLE checkpoints (cycle TEXT NOT NULL, step TEXT NOT NULL, item TEXT NOT NULL, job_id TEXT,
    status TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (cycle, step, item));
CREATE TABLE pipeline_lock (id INTEGER PRIMARY KEY CHECK (id = 1), job_id TEXT NOT NULL, task TEXT NOT NULL,
    acquired_at TEXT NOT NULL);
CREATE TABLE forecast_runs (cycle TEXT NOT NULL, couple TEXT NOT NULL, state TEXT NOT NULL, disease_code TEXT NOT NULL,
    ou_level TEXT NOT NULL, alert_name TEXT, opened_at TEXT NOT NULL, closed_at TEXT, PRIMARY KEY (cycle, couple, opened_at));
CREATE UNIQUE INDEX one_open_run ON forecast_runs(state) WHERE state = 'open';
CREATE TABLE pipeline_cycle (id INTEGER PRIMARY KEY CHECK (id = 1), cycle TEXT NOT NULL);
CREATE TABLE pipeline_events (id INTEGER PRIMARY KEY AUTOINCREMENT, cycle TEXT NOT NULL, at TEXT NOT NULL, step TEXT,
    item TEXT, event TEXT NOT NULL, job_id TEXT, actor TEXT, request_id TEXT, detail TEXT);
CREATE INDEX ix_pipeline_events_cycle ON pipeline_events(cycle, id);
INSERT INTO pipeline_cycle VALUES (1, '202504');
INSERT INTO pipeline_events (cycle, at, step, item, event, actor) VALUES
    ('202504', '2026-10-20T10:00:00.000000', 'data_import', 'import_gee', 'launched', 'alice'),
    ('202504', '2026-10-20T11:00:00.000000', NULL, NULL, 'cycle_closed', 'alice'),
    ('202504', '2026-10-20T12:00:00.000000', NULL, NULL, 'mode_changed', 'alice'),
    ('202504', '2026-10-20T13:00:00.000000', NULL, NULL, 'cycle_chosen', 'bob'),
    ('202504', '2026-10-20T14:00:00.000000', 'data_import', 'import_gee', 'launched', 'bob');
INSERT INTO checkpoints VALUES ('202504', 'data_import', 'import_gee', 'j2', 'success', '2026-10-20T14:01:00');
INSERT INTO forecast_runs VALUES
    ('202504', 'ADJ/Malaria', 'closed', 'x', '6', NULL, '2026-10-20T10:30:00.000000', '2026-10-20T10:40:00'),
    ('202504', 'COM/Malaria', 'open', 'x', '6', NULL, '2026-10-20T15:00:00.000000', NULL);
"""


def test_a_store_keyed_by_month_is_split_into_passes_at_each_cycle_closed(checkpoint_store, month, tmp_path):
    legacy = sqlite3.connect(tmp_path / "etlhub.db")
    legacy.executescript(_LEGACY_SCHEMA)
    legacy.close()
    (tmp_path / "uploads" / "202504").mkdir(parents=True)
    (tmp_path / "uploads" / "202504" / "config_Malaria.json").write_text("{}")

    (line,) = checkpoint_store.migrate()

    assert line.startswith(f"{tmp_path / 'etlhub.db'}: version 0 -> 3, backup ")
    (backup,) = tmp_path.glob("etlhub.db.v0-*.bak")
    assert "cycle" in {r[1] for r in sqlite3.connect(backup).execute("PRAGMA table_info(checkpoints)")}
    (cycle,) = [c for c in checkpoint_store.cycles() if c["cycle"] == "202504"]

    second, first = cycle["passes"]
    assert (first["state"], first["started_by"], second["state"], second["started_by"]) == (
        "complete", "alice", "active", "bob")
    assert [e["event"] for e in checkpoint_store.journal(first["id"])] == [
        "launched", "cycle_closed", "mode_changed", "cycle_chosen"]
    assert [e["event"] for e in checkpoint_store.journal(second["id"])] == ["launched"]
    state = checkpoint_store.progress()
    assert (state["pass"]["id"], state["run"]["couple"]) == (second["id"], "COM/Malaria")
    assert _status(state, "data_import", "import_gee") == "success"
    assert (tmp_path / "input" / "202504" / second["id"] / "config_Malaria.json").is_file()  # pass folders
    assert checkpoint_store.cycles() == [cycle]  # migrated once: the ids stay
    assert checkpoint_store.migrate() == []


# --- schema migrations, by hand only (db-migrations.md) -------------------------------------------

def test_a_db_behind_this_code_is_refused_until_migrated_by_hand(checkpoint_store, tmp_path):
    from etlhub.infrastructure.checkpoint_store import SchemaVersionError
    with closing(sqlite3.connect(tmp_path / "etlhub.db")) as db:
        db.executescript(_LEGACY_SCHEMA)

    for read in (checkpoint_store.progress, checkpoint_store.check_schema):
        with pytest.raises(SchemaVersionError, match="version 0.*python -m etlhub.migrate"):
            read()
    assert checkpoint_store.migrate(check=True) == [f"{tmp_path / 'etlhub.db'}: version 0 -> 3"]
    assert not list(tmp_path.glob("*.bak"))  # check changes nothing

    checkpoint_store.migrate()
    checkpoint_store.check_schema()
    assert checkpoint_store.progress()["pass"]


def test_a_db_newer_than_this_code_is_refused_even_by_migrate(checkpoint_store, tmp_path):
    from etlhub.infrastructure.checkpoint_store import SchemaVersionError
    checkpoint_store.progress()  # a new db: created at SCHEMA_VERSION
    with closing(sqlite3.connect(tmp_path / "etlhub.db")) as db:
        assert db.execute("PRAGMA user_version").fetchone() == (3,)
        db.execute("PRAGMA user_version = 4")  # left by a newer etlhub

    for call in (checkpoint_store.progress, checkpoint_store.migrate):
        with pytest.raises(SchemaVersionError, match="version 4, newer than this code"):
            call()


def test_the_test_mode_db_in_redis_is_migrated_with_its_own_backup(checkpoint_store, tmp_path):
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(_LEGACY_SCHEMA)
        checkpoint_store._blob.set(db.serialize())
    checkpoint_store.mode["test_mode"] = True

    (line,) = checkpoint_store.migrate()

    assert line.startswith("the test-mode db (Redis pipeline:dry_run:db): version 0 -> 3")
    (backup,) = tmp_path.glob("test_mode.db.v0-*.bak")
    assert "cycle" in {r[1] for r in sqlite3.connect(backup).execute("PRAGMA table_info(checkpoints)")}
    assert [c["cycle"] for c in checkpoint_store.cycles() if c["passes"]] == ["202504"]


# --- migration 2: FOREIGN KEY pass_id -> passes(id) (foreign-keys.md) ----------------------------

_FK_TABLES = ("checkpoints", "forecast_runs", "pipeline_events", "availability_checks")


def _v2_schema():
    """Today's _SCHEMA without the PASS_CONFIG columns of passes (migration 3)."""
    from etlhub.infrastructure.checkpoint_store import _SCHEMA
    return re.sub(r",\n    -- Its configuration.*?dhis_url +TEXT", "", _SCHEMA, count=1, flags=re.S)


def _v1_db(path, orphan=False):
    """A db at schema version 1: today's tables without their FOREIGN KEY, external_data still in forecast_runs."""
    from etlhub.infrastructure.checkpoint_store import _SCHEMA
    with closing(sqlite3.connect(path)) as db:
        db.executescript(_v2_schema().replace(" REFERENCES passes(id)", "") + """
            ALTER TABLE forecast_runs ADD COLUMN external_data TEXT DEFAULT 'none';
            PRAGMA user_version = 1;
            INSERT INTO passes VALUES ('p1', '202611', 'active', '2026-11-01T08:00:00', 'alice');
            INSERT INTO checkpoints VALUES ('p1', 'data_import', 'import_gee', 'j1', 'success', '2026-11-01T09:00:00');
            INSERT INTO forecast_runs (pass_id, couple, state, disease_code, ou_level, opened_at)
                VALUES ('p1', 'ADJ/Malaria', 'open', 'x', '6', '2026-11-01T10:00:00');
            INSERT INTO pipeline_events (cycle, pass_id, at, event) VALUES
                ('202611', NULL, '2026-11-01T07:00:00', 'mode_changed'), ('202611', 'p1', '2026-11-01T08:00:00', 'launched');
            INSERT INTO availability_checks (cycle, pass_id, task, params, checked_at, section)
                VALUES ('202611', NULL, 'import_gee', '{}', '2026-10-31T08:00:00', '{}');
        """)
        if orphan:  # a pass deleted by hand
            db.execute("INSERT INTO checkpoints VALUES ('gone', 'data_import', 'import_gee', NULL, 'success', 'x')")
            db.commit()


def test_migration_2_adds_the_foreign_keys_and_keeps_every_row(checkpoint_store, tmp_path):
    db_path = tmp_path / "etlhub.db"
    _v1_db(db_path)

    (line,) = checkpoint_store.migrate()

    assert line.startswith(f"{db_path}: version 1 -> 3, backup ")
    (backup,) = tmp_path.glob("etlhub.db.v1-*.bak")
    with closing(sqlite3.connect(backup)) as db:
        assert db.execute("PRAGMA foreign_key_list(checkpoints)").fetchall() == []
    with closing(sqlite3.connect(db_path)) as db:
        for table in _FK_TABLES:
            fks = [(r[2], r[3], r[4]) for r in db.execute(f"PRAGMA foreign_key_list({table})")]
            assert fks == [("passes", "pass_id", "id")], table
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone() == ((2,) if table == "pipeline_events" else (1,))
        assert "external_data" not in {r[1] for r in db.execute("PRAGMA table_info(forecast_runs)")}
        indexes = {name for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL")}
        assert indexes >= {"one_active_pass", "ix_checkpoints_job_id", "one_open_run_per_pass", "ix_pipeline_events_pass",
                           "ix_pipeline_events_job_id", "ix_availability_checks"}
        assert db.execute("SELECT id, event FROM pipeline_events ORDER BY id").fetchall() == [
            (1, "mode_changed"), (2, "launched")]  # the journal keeps its ids...
        new = db.execute("INSERT INTO pipeline_events (cycle, at, event) VALUES ('202611', 'x', 'e')").lastrowid
        assert new == 3  # ...and goes on after them
        assert not any(name.endswith("_v1") for (name,) in db.execute("SELECT name FROM sqlite_master"))
    assert checkpoint_store.migrate() == []


def test_migration_2_refuses_an_orphan_row_and_leaves_the_db_at_version_1(checkpoint_store, tmp_path):
    _v1_db(tmp_path / "etlhub.db", orphan=True)

    with pytest.raises(sqlite3.IntegrityError, match="checkpoints"):
        checkpoint_store.migrate()

    with closing(sqlite3.connect(tmp_path / "etlhub.db")) as db:
        assert db.execute("PRAGMA user_version").fetchone() == (1,)
        assert db.execute("PRAGMA foreign_key_list(checkpoints)").fetchall() == []
        assert db.execute("SELECT count(*) FROM checkpoints").fetchone() == (2,)


@pytest.mark.parametrize("test_mode", [False, True])
def test_the_store_refuses_a_row_whose_pass_does_not_exist(checkpoint_store, test_mode):
    checkpoint_store.mode["test_mode"] = test_mode

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        with checkpoint_store._transaction() as conn:
            conn.execute("INSERT INTO checkpoints VALUES ('nope', 'data_import', 'import_gee', NULL, 'success', 'x')")


def test_dryrun_is_the_test_mode(checkpoint_store):
    assert (checkpoint_store.progress()["test_mode"], checkpoint_store.progress()["dry_run"]) == (False, False)
    checkpoint_store.mode["test_mode"] = True
    assert (checkpoint_store.progress()["test_mode"], checkpoint_store.progress()["dry_run"]) == (True, True)


def test_a_test_pass_that_stored_dry_run_false_still_never_writes(checkpoint_store):
    checkpoint_store.mode["test_mode"] = True
    p = checkpoint_store.start_pass()
    with checkpoint_store._transaction() as conn:  # started on Home with Dry run NO, before DRYRUN = TEST MODE
        conn.execute("UPDATE passes SET dry_run = 0 WHERE id = ?", (p["id"],))

    checkpoint_store.start("import_gee", "j1")

    assert checkpoint_store.progress()["pass"]["dry_run"] is True  # what etlui shows
    launched = [e["detail"]["dry_run"] for e in checkpoint_store.journal(p["id"]) if e["event"] == "launched"]
    assert launched == [True]  # the mode's, not the stored value


# --- carry-over of Data Import to a new pass of the cycle (cycle-passes.md § 11) ---------------

PARAMS = {t: {"task": t, "org_units": "ou:LEVEL-6;P1"} for t in ("import_gee", "import_pivot_com", "import_pivot_csb")}


def _launch_import(store, task, params=PARAMS, confirm=False, state="success"):
    """What IngestionService does: the import's parameters in its launched event, all of them to carry the others over."""
    job_id = f"{task}_{next(_ids)}"
    store.start(task, job_id, confirm, carry_over=params)
    if state:
        store.finish(job_id, state)
    return job_id


def _imports_approved(store, params=PARAMS):
    jobs = {t: _launch_import(store, t, params) for t in PARAMS}
    store.decide_imports("approve")
    return jobs


def _new_pass(store, task="import_gee", params=PARAMS):
    """Abandons the shown pass, then starts the next one of the cycle with a launch of `task` (left running)."""
    old = store.progress()["pass"]["id"]
    store.abandon(old)
    _launch_import(store, task, params, state=None)
    return old, store.progress()


def test_a_new_pass_carries_over_the_imports_and_their_approval_done_with_the_same_parameters(checkpoint_store, month):
    jobs = _imports_approved(checkpoint_store)
    _pass(checkpoint_store, "build_analytics")

    old, state = _new_pass(checkpoint_store)

    assert {i: _status(state, "data_import", i) for i in ("import_gee", "import_pivot_com", "import_pivot_csb",
                                                          "approve_imports", "build_analytics")} == {
        "import_gee": "running",  # the launch that started the pass: relaunched, not carried
        "import_pivot_com": "success", "import_pivot_csb": "success", "approve_imports": "success",
        "build_analytics": "pending"}  # never carried: approving leads to it
    carried = [e for e in _journal(checkpoint_store) if e["event"] == "carried_over"]
    assert [(e["item"], e["job_id"], e["detail"]["from_pass"]) for e in carried] == [
        ("import_pivot_com", jobs["import_pivot_com"], old), ("import_pivot_csb", jobs["import_pivot_csb"], old),
        ("approve_imports", None, old)]
    assert carried[0]["detail"]["dry_run"] is False and carried[0]["detail"]["status"] == "success"


def test_other_parameters_another_dryrun_or_an_unrecorded_launch_are_not_carried(checkpoint_store, month):
    for task in ("import_gee", "import_pivot_csb"):
        _launch_import(checkpoint_store, task)
    _pass(checkpoint_store, "import_pivot_com")  # launched without parameters (before they were recorded)
    checkpoint_store.decide_imports("approve")

    _, state = _new_pass(checkpoint_store, "import_pivot_csb", {**PARAMS, "import_gee": {"task": "import_gee", "org_units": "P2"}})

    assert [_status(state, "data_import", i) for i in ("import_gee", "import_pivot_com", "approve_imports")] == [
        "pending", "pending", "pending"]  # gee: PARENT_OU changed; com: no parameters; approve: com not carried
    checkpoint_store.finish(state["lock"]["job_id"], "success")

    with checkpoint_store._transaction() as conn:  # a production import done in dry run before DRYRUN = TEST MODE
        conn.execute("UPDATE pipeline_events SET detail = json_set(detail, '$.dry_run', json('true'))"
                     " WHERE event = 'launched' AND item = 'import_pivot_csb'")
    _, state = _new_pass(checkpoint_store, "import_gee")
    assert _status(state, "data_import", "import_pivot_csb") == "pending"  # it wrote nothing: not carried


def test_a_carried_item_is_relaunched_only_with_confirmation_and_carries_on_to_the_next_pass(checkpoint_store, month):
    jobs = _imports_approved(checkpoint_store)
    _, state = _new_pass(checkpoint_store)
    checkpoint_store.finish(state["lock"]["job_id"], "success")

    with pytest.raises(ConfirmationRequiredError):
        _launch_import(checkpoint_store, "import_pivot_com")
    _launch_import(checkpoint_store, "import_pivot_com", confirm=True)  # free choice of the operator

    _, state = _new_pass(checkpoint_store, "import_gee")
    carried = {e["item"]: e["job_id"] for e in _journal(checkpoint_store) if e["event"] == "carried_over"}
    assert carried["import_pivot_csb"] == jobs["import_pivot_csb"]  # carried twice: still the job that imported
    assert carried["import_pivot_com"] != jobs["import_pivot_com"]  # the relaunch, the most recent success


def test_the_first_pass_of_a_cycle_has_nothing_to_carry(checkpoint_store, month):
    _imports_approved(checkpoint_store)
    checkpoint_store.pause()
    month("202611")

    _launch_import(checkpoint_store, "import_gee", state=None)

    assert [_status(checkpoint_store.progress(), "data_import", i) for i in ("import_pivot_com", "approve_imports")] == [
        "pending", "pending"]


def test_release_lock_of_a_given_job_leaves_the_lock_of_another_one(checkpoint_store):
    checkpoint_store.start("import_gee", "newer")

    assert checkpoint_store.release_lock("asked_about") is None
    assert checkpoint_store.progress()["lock"]["job_id"] == "newer"
    assert checkpoint_store.release_lock("newer") == "newer"


# --- migration 3 and the configuration fixed by a pass (pass-config.md) -----------------------------------------

def test_migration_3_adds_the_pass_configuration_and_leaves_existing_passes_unfixed(checkpoint_store, tmp_path):
    _v1_db(tmp_path / "etlhub.db")

    checkpoint_store.migrate()

    with closing(sqlite3.connect(tmp_path / "etlhub.db")) as db:
        assert db.execute("PRAGMA user_version").fetchone() == (3,)
        assert db.execute("SELECT id, gee_variables, parent_ou, log_level, dry_run, dhis_url FROM passes").fetchall() == [
            ("p1", None, None, None, None, None)]
    assert checkpoint_store.pass_config() == {**dict.fromkeys(PASS_CONFIG), "dry_run": False}  # p1: Redis, as before;
    # DRYRUN: the mode's (production), for passes from before too
    checkpoint_store.start("import_pivot_com", "j")
    last = _journal(checkpoint_store)[-1]
    assert (last["event"], last["detail"]["dry_run"]) == ("launched", False)  # production: DRYRUN = TEST MODE


def test_a_pass_fixes_its_configuration_when_it_starts(checkpoint_store):
    p = checkpoint_store.start_pass(gee_variables="v1,v3")
    fixed = {"gee_variables": "v1,v3", "parent_ou": "ou_parent", "log_level": "INFO", "dry_run": False,
             "dhis_url": "https://dhis2.test"}

    assert {c: p[c] for c in PASS_CONFIG} == fixed
    checkpoint_store.live.update(parent_ou="ou_edited", log_level="DEBUG")  # Admin Config, after the start
    assert checkpoint_store.pass_config() == fixed
    assert {c: checkpoint_store.progress()["pass"][c] for c in PASS_CONFIG} == fixed
    (started,) = [e for e in checkpoint_store.journal(p["id"]) if e["event"] == "pass_started"]
    assert started["detail"] == fixed
    checkpoint_store.pause()
    assert checkpoint_store.pass_config() is None  # no active pass
    checkpoint_store.resume(p["id"])
    assert checkpoint_store.pass_config() == fixed  # resumed as it was
    checkpoint_store.start("import_gee", "j1")
    last = _journal(checkpoint_store)[-1]
    assert (last["event"], last["detail"]["dry_run"]) == ("launched", False)  # production: DRYRUN = TEST MODE


def test_a_launch_from_a_session_on_another_dhis2_is_refused_and_writes_nothing(checkpoint_store):
    p = checkpoint_store.start_pass()
    checkpoint_store.live["dhis_url"] = "https://other.dhis2"  # someone logged in elsewhere

    with pytest.raises(PipelineBlockedError, match="runs on the DHIS2 https://dhis2.test, fixed when it started"):
        checkpoint_store.start("import_gee", "j1")
    assert checkpoint_store.held_lock() is None
    assert [e["event"] for e in checkpoint_store.journal(p["id"])] == ["pass_started"]


def test_a_pass_started_by_a_launch_fixes_the_configuration_of_that_moment(checkpoint_store):
    checkpoint_store.start("import_gee", "j1")

    assert checkpoint_store.pass_config() == {"gee_variables": None, "parent_ou": "ou_parent", "log_level": "INFO",
                                              "dry_run": False, "dhis_url": "https://dhis2.test"}  # GEE: all of them
