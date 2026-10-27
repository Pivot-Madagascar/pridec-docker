"""GET /import_availability: the report of etl/scripts/check_import_availability.py, shared in the cycle, journaled and tracked."""
import pandas as pd
import pytest

from etlhub.application.use_cases.availability_service import AvailabilityService
from etlhub.core.dependencies import get_availability_service

TASKS = ["import_gee", "import_pivot_com", "import_pivot_csb"]
ELEMENT = {"code": "pridec_historic_COMMalaria", "raw": {"202609": 3}, "analytics": {"202609": 0},
           "last_updated": "2026-10-01T08:00:00.000+0000", "imported": True, "analytics_up_to_date": False, "error": None}
FAILED = {**ELEMENT, "code": "x", "raw": None, "analytics": None, "imported": False, "analytics_up_to_date": None,
          "error": "409 Conflict"}


class FakeScript:
    """The two functions of the script: the plan (no DHIS2) and the report of some sections (counts DHIS2 calls)."""

    def __init__(self):
        self.parent_ou, self.calls, self.error = "P1", [], None

    def plan(self):
        if self.error:
            raise self.error
        return {"dhis_url": "http://dhis2.test", "imports": [
            {"task": t, "elements": ["e"], "periods": ["202609"], "org_units": f"ou:LEVEL-6;{self.parent_ou}"} for t in TASKS]}

    def report(self, tasks):
        self.calls.append(tasks)
        return {"checked_at": "x", "dhis_url": "http://dhis2.test", "last_analytics": f"build-{len(self.calls)}",
                "imports": [{"task": t, "periods": ["202609"], "org_units": "ou:LEVEL-6;P1",
                             "elements": [ELEMENT, FAILED] if t == "import_pivot_com" else [ELEMENT]} for t in tasks]}


@pytest.fixture
def script(app, checkpoint_store):
    fake = FakeScript()
    app.dependency_overrides[get_availability_service] = lambda: AvailabilityService(checkpoint_store, fake.plan, fake.report)
    yield fake
    app.dependency_overrides.pop(get_availability_service, None)


def _launch(store, task):
    job_id = f"{task}_{len(store.contexts):08x}"
    store.start(task, job_id, confirm=True)
    store.finish(job_id, "success")


def _pass_id(store):
    _launch(store, "import_gee")
    return store.progress()["pass"]["id"]


def test_the_first_check_asks_dhis2_for_every_section_and_is_journaled(client, script, checkpoint_store):
    pass_id = _pass_id(checkpoint_store)

    response = client.get("/import_availability")

    assert response.status_code == 200
    body = response.json()
    assert script.calls == [TASKS]
    assert [(i["task"], i["reused"], i["pass_id"]) for i in body["imports"]] == [(t, False, pass_id) for t in TASKS]
    assert body["last_analytics"] == "build-1"
    event = checkpoint_store.journal(pass_id)[-1]
    assert (event["event"], event["step"]) == ("availability_checked", "data_import")
    assert event["detail"] == {"checked": TASKS, "missing": 0, "analytics_behind": 3, "errors": 1}
    # journaled = tracked, even outside TRACKED_ENDPOINTS
    from etlhub.infrastructure.request_tracker import get_request_tracker
    assert get_request_tracker().get(response.headers["X-Request-ID"])["status_code"] == 200
    # a read is not pipeline work: the pass's event count ignores it
    counted = next(p for c in checkpoint_store.cycles() for p in c["passes"] if p["id"] == pass_id)
    assert counted["events"] == 3  # pass_started, launched, succeeded


def test_the_next_user_gets_the_stored_report_without_asking_dhis2(client, script, checkpoint_store):
    pass_id = _pass_id(checkpoint_store)
    first = client.get("/import_availability").json()

    again = client.get("/import_availability").json()

    assert script.calls == [TASKS]  # DHIS2 asked once
    assert [i["reused"] for i in again["imports"]] == [True, True, True]
    assert [i["checked_at"] for i in again["imports"]] == [i["checked_at"] for i in first["imports"]]
    assert again["imports"][1]["elements"] == first["imports"][1]["elements"]
    assert again["last_analytics"] == "build-1"
    assert checkpoint_store.journal(pass_id)[-1]["event"] == "availability_reused"


def test_a_launched_import_invalidates_its_own_section_only(client, script, checkpoint_store):
    _pass_id(checkpoint_store)
    client.get("/import_availability")
    checkpoint_store.start("import_pivot_com", "import_pivot_com_0000000a")  # running: the launch is enough

    body = client.get("/import_availability").json()

    assert script.calls == [TASKS, ["import_pivot_com"]]
    assert [i["reused"] for i in body["imports"]] == [True, False, True]
    assert body["last_analytics"] == "build-2"  # the latest check's


def test_other_parameters_or_refresh_ask_dhis2_again(client, script, checkpoint_store):
    _pass_id(checkpoint_store)
    client.get("/import_availability")

    script.parent_ou = "P2"  # PARENT_OU changed in the config
    client.get("/import_availability")
    client.get("/import_availability?refresh=true")

    assert script.calls == [TASKS, TASKS, TASKS]


def test_a_check_that_cannot_run_is_a_500_and_is_journaled(client, script, checkpoint_store):
    pass_id = _pass_id(checkpoint_store)
    script.error = EnvironmentError("Required environment variable 'PARENT_OU' is missing.")

    response = client.get("/import_availability")

    assert response.status_code == 500
    assert response.json()["message"].startswith("Import availability check failed: Required environment variable")
    assert checkpoint_store.journal(pass_id)[-1]["detail"]["error"].startswith("Required environment variable")


def test_a_check_before_the_first_launch_needs_no_pass_and_is_shared_with_the_pass_that_follows(
        client, script, checkpoint_store):
    assert client.get("/import_availability").json()["imports"][0]["pass_id"] is None
    assert checkpoint_store.progress()["pass"] is None  # a read never starts a pass

    _launch(checkpoint_store, "import_pivot_csb")  # starts the cycle's pass
    body = client.get("/import_availability").json()

    assert script.calls == [TASKS, ["import_pivot_csb"]]
    assert [i["reused"] for i in body["imports"]] == [True, True, False]


# --- the script itself (DHIS2 faked at its two entry points) ------------------------------

@pytest.fixture
def dhis2(monkeypatch):
    from etl.scripts import check_import_availability as script, config
    for name, value in {"get_dhis_url": "http://dhis2.test", "get_dhis_token": "t", "get_parent_ou": "P1",
                        "get_gee_variables": ["pridec_climate_precipitation", "unknown_code"]}.items():
        monkeypatch.setattr(config, name, lambda value=value: value)
    monkeypatch.setattr(script, "create_period_range", lambda start: "pe:202608;202609")
    stored, queries = [], []

    def get(url, token, path, params=None):
        if path == "/api/system/info.json":
            return {"lastAnalyticsTableSuccess": "2026-10-20T13:36:07.058"}
        queries.append(params)
        if params["dataElement"] == "unknown_code":
            raise RuntimeError("409 Conflict")
        return {"dataValues": [v for v in stored if v["period"] in params["period"]]}

    def analytics(dx_query, pe_query, **kwargs):  # the analytics tables hold 202608 only
        return pd.DataFrame([{"dx": dx_query[3:], "ou": "a", "pe": "202608", "value": "1"}])

    monkeypatch.setattr(script, "_get", get)
    monkeypatch.setattr(script, "get_dataElements", analytics)
    return script, stored, queries


def test_raw_and_analytics_counts_per_period(dhis2):
    script, stored, _ = dhis2
    stored += [{"orgUnit": ou, "period": pe, "lastUpdated": f"2026-10-0{i}"}
               for i, (ou, pe) in enumerate([("a", "202608"), ("a", "202609"), ("b", "202609")], 1)]

    report = script.availability_report()

    assert report["last_analytics"] == "2026-10-20T13:36:07.058"
    assert [i["task"] for i in report["imports"]] == TASKS
    gee = report["imports"][0]
    assert gee["org_units"] == "ou:LEVEL-6;P1"
    ok, unknown = gee["elements"]
    assert ok == {"code": "pridec_climate_precipitation", "raw": {"202608": 1, "202609": 2},
                  "analytics": {"202608": 1, "202609": 0}, "last_updated": "2026-10-03",
                  "imported": True, "analytics_up_to_date": False, "error": None}
    assert (unknown["raw"], unknown["imported"], unknown["error"]) == (None, False, "409 Conflict")  # its row only


def test_a_period_without_stored_value_is_not_imported(dhis2):
    script, stored, _ = dhis2
    stored.append({"orgUnit": "a", "period": "202608", "lastUpdated": "2026-10-01"})

    com = script.availability_report()["imports"][1]["elements"][0]

    assert (com["raw"], com["imported"], com["analytics_up_to_date"]) == ({"202608": 1, "202609": 0}, False, True)


def test_only_the_asked_sections_query_dhis2_with_their_own_org_units(dhis2):
    script, _, queries = dhis2

    report = script.availability_report(["import_pivot_csb"])

    assert [i["task"] for i in report["imports"]] == ["import_pivot_csb"]
    assert {(q["children"], len(q["orgUnit"])) for q in queries} == {("false", len(script.CSB_IDS))}
    assert [s["org_units"] for s in script.availability_plan()["imports"]][:2] == ["ou:LEVEL-6;P1"] * 2
