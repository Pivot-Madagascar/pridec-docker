"""The mode per user and its isolation, end to end, in a headless browser against the whole stack.

One scenario, its steps in order (etlhub/docs/decision-design/mode-isolation/mode-isolation.md):
Home asks the mode then the cycle, a test pass starts; step 1 and one CSB/Malaria run go through the worker in test
mode, every DHIS2 write in dry run; the fetch_* files land in test/input (B2); the forecast container mounts the test
folders; switching mode mid-pass is refused while a job runs, then asks pause or abandon; production reads nothing of
test mode; the Journal says why the pass was paused; ./input and ./output are untouched. The pass is abandoned at the
end. Needs a stack with no active test pass and no job running.
"""
import json
import time

import pytest
from playwright.sync_api import expect

from conftest import RELAUNCH_IMPORTS, ROOT, UI, USERNAME, production_files

pytestmark = pytest.mark.incremental

COUPLE = "CSB/Malaria"  # test mode's default config and external data are a CSB/Malaria set (default-input-files.md)
FETCHED = {"fetch_disease": "disease_data.json", "fetch_climate": "climate_data.json",
           "fetch_geojson": "orgUnit_poly.geojson"}
run: dict = {}  # what a step hands to the next ones: pass id, job ids, production files before


@pytest.fixture(scope="module", autouse=True)
def abandon_the_pass(stack):
    """Leaves no active test pass behind: the next run starts the month again."""
    yield
    if pass_id := run.get("pass_id"):
        stack.send("PUT", "/pipeline/mode", data={"test_mode": True})
        stack.send("POST", f"/pipeline/passes/{pass_id}/abandon")


def test_a_new_session_starts_in_test_mode_on_a_free_stack(stack):
    state = stack.state()
    assert state["test_mode"] is True
    assert state["lock"] is None, f"a job is running: {state['lock']}"
    assert not (state["pass"] and state["pass"]["state"] == "active"), f"a test pass is active: {state['pass']}"
    run["production_before"] = production_files()


def test_home_asks_the_mode_then_the_cycle_and_starts_a_test_pass(stack):
    page = stack.page
    page.goto(f"{UI}/")
    dialog = page.locator('[data-test="cycle-dialog"]')
    expect(dialog).to_be_visible(timeout=15000)
    html = dialog.inner_html()
    assert 0 <= html.find('aria-label="Test mode"') < html.find('data-test="cycle-picker"'), "the mode comes first"
    expect(dialog.locator('[data-test="mode-btn"]', has_text="YES")).to_have_attribute("data-state", "on")
    month = time.strftime("%Y-%m")
    expect(dialog.locator('[data-test="cycle-picker"]')).to_have_attribute("value", month)
    page.wait_for_timeout(500)  # after the fade-in
    stack.shot("1_home_dialog")

    dialog.get_by_role("button", name="Continue").click()
    expect(dialog).to_be_hidden()
    page.locator('[role="radio"][value="new"]').click()
    page.get_by_role("button", name="Start", exact=True).click()
    impact = page.locator('[data-test="impact-dialog"]')  # the month has a paused pass: a new one beside it is confirmed
    page.wait_for_function("() => location.pathname === '/forecast' || document.querySelector('[data-test=impact-dialog]')",
                           timeout=30000)
    if impact.count():
        impact.get_by_role("checkbox").click()
        impact.get_by_role("button", name="Confirm").click()
    page.wait_for_url("**/forecast", timeout=30000)

    state = stack.state()
    assert (state["test_mode"], state["cycle"], state["pass"]["state"]) == (True, month.replace("-", ""), "active")
    run["pass_id"] = state["pass"]["id"]


def test_step_1_runs_in_the_worker_in_test_mode_with_dhis2_writes_in_dry_run(stack):
    # An import done in another test pass of the month, same parameters and dry run, is carried over: not relaunched.
    imports = ("import_gee", "import_pivot_com", "import_pivot_csb")
    for task in imports:
        done = stack.item(task)["status"] == "success"
        if RELAUNCH_IMPORTS or not done:
            stack.run_job(task, confirm=done)  # test mode: a dry run (DRYRUN = TEST MODE)
    if stack.item("approve_imports")["status"] != "success":
        status, answer = stack.send("POST", "/pipeline/imports/approve", data={"decision": "approve"})
        assert status == 200, answer
    stack.run_job("build_analytics")

    journal = stack.get(f"/pipeline/passes/{run['pass_id']}/journal")[1]
    done = {e["item"] for e in journal if e["event"] in ("succeeded", "carried_over", "decided")}  # decided: approve
    assert done >= {*imports, "approve_imports", "build_analytics"}
    # The journal API shows a job once, at its end, with the launch's detail (JournalService._job_outcomes).
    ran = [e for e in journal if e["event"] == "succeeded"]
    assert ran and all(e["mode"] == "test" and e["detail"].get("dry_run") is True for e in ran)


def test_the_fetch_files_of_a_test_run_land_in_test_input(stack):
    status, answer = stack.send("POST", "/pipeline/runs", data={"source": "CSB", "disease": "Malaria"})
    assert status == 201, answer
    for name in ("config", "external_data"):
        status, answer = stack.send("POST", f"/input/files/{name}/from-default")
        assert status == 200, answer
    for task, name in FETCHED.items():
        stack.run_job(task)
        assert (ROOT / "test" / "input" / name).is_file(), f"{name} not in test/input"
    stack.run_job("validate_inputs")
    assert (ROOT / "test" / "input" / "config_valid.json").is_file()


def test_the_forecast_container_mounts_the_test_folders(stack):
    job_id = stack.launch("forecast")
    end = stack.wait(job_id)
    run["forecast_job"] = job_id
    if end["status"] == "error" and "The data must contain the requested date range" in (end.get("logs") or ""):
        # The container read test/input/config.json: its first month is the test forecast_start minus month_analysis.
        config = json.loads((ROOT / "test" / "input" / "config.json").read_text())
        start = int(config["forecast_start"][:4]) * 12 + int(config["forecast_start"][4:]) - 1 - config["month_analysis"]
        assert f"start date of {start // 12}-{start % 12 + 1:02d}-01" in end["logs"], "not the test config"
        pytest.xfail("known: forecast_start = the cycle goes past the test data (pivot_forecast.sh uses 202601)")
    assert end["status"] == "success", end.get("message")
    assert (ROOT / "test" / "output" / "forecast_report.html").is_file()


def test_switching_mode_while_a_job_runs_asks_then_is_refused(stack):
    job_id = stack.launch("forecast", confirm=True)  # anything long enough: the forecast container starts
    status, answer = stack.send("PUT", "/pipeline/mode", data={"test_mode": False})
    assert status == 409 and answer["code"] == "confirmation_required", answer
    assert answer["impact"]["actions"] == ["pause", "abandon"] and answer["impact"]["pass_id"] == run["pass_id"]
    status, answer = stack.send("PUT", "/pipeline/mode", data={"test_mode": False, "pass_action": "pause"})
    assert status == 409 and "one job at a time" in answer["message"], answer

    stack.page.goto(f"{UI}/forecast")
    expect(stack.page.locator(".lock-banner")).to_contain_text(job_id)
    stack.shot("2_job_running")
    stack.wait(job_id)
    assert stack.state()["test_mode"] is True  # nothing switched


def test_the_switch_in_the_ui_offers_pause_or_abandon_and_pauses_the_pass(stack):
    page = stack.page
    page.reload()
    page.locator('[data-test="mode-btn"]', has_text="NO").first.click()
    dialog = page.locator('[data-test="impact-dialog"]')
    expect(dialog).to_be_visible(timeout=15000)
    expect(dialog.locator('[data-test="impact-action-pause"]')).to_be_disabled()  # until the impact is read
    expect(dialog.locator('[data-test="impact-action-abandon"]')).to_be_visible()
    expect(dialog.get_by_role("button", name="Confirm")).to_have_count(0)
    page.wait_for_timeout(500)
    stack.shot("3_switch_dialog")

    dialog.get_by_role("checkbox").click()
    dialog.locator('[data-test="impact-action-pause"]').click()
    expect(dialog).to_be_hidden(timeout=15000)
    expect(page.locator('[data-test="mode-btn"]', has_text="NO").first).to_have_attribute("data-state", "on")
    assert stack.state()["test_mode"] is False


def test_production_reads_nothing_of_test_mode(stack):
    pass_id, job_ids = run["pass_id"], {run["forecast_job"]}
    cycles = stack.get("/pipeline/cycles")[1]
    assert pass_id not in json.dumps(cycles)
    assert all(p["mode"] == "production" for c in cycles for p in c["passes"])
    assert stack.get(f"/pipeline/passes/{pass_id}/journal")[1] == []
    assert stack.get(f"/api/tracking/etl-logs/{run['forecast_job']}")[0] == 404
    requests = stack.get("/api/tracking/requests?limit=500")[1]
    assert not job_ids & {r.get("job_id") for r in requests}

    stack.page.goto(f"{UI}/journal")
    expect(stack.page.get_by_text(pass_id)).to_have_count(0)
    stack.shot("4_journal_production")


def test_back_in_test_mode_the_journal_says_why_the_pass_was_paused(stack):
    production = stack.state()
    if production["pass"] and production["pass"]["state"] == "active":
        pytest.skip("production has an active pass: going back would ask to pause or abandon it")
    status, answer = stack.send("PUT", "/pipeline/mode", data={"test_mode": True})
    assert status == 200, answer

    paused = stack.get(f"/pipeline/passes/{run['pass_id']}/journal")[1][-1]
    assert (paused["event"], paused["actor"], paused["detail"]["cause"]) == ("paused", USERNAME, "mode_change")
    assert paused["detail"]["reason"] == "Mode changed manually by the user: from test to production"

    stack.page.goto(f"{UI}/journal?pass={run['pass_id']}")
    expect(stack.page.get_by_text("Mode changed manually by the user: from test to production")).to_be_visible()
    stack.shot("5_journal_test")


def test_the_production_folders_are_untouched(stack):
    assert production_files() == run["production_before"]
