import json
from datetime import date

import pytest

from etlhub.application.use_cases import calc_alerts as module

ALERT = {"dataValues": [{"dataElement": "pridec_alert_CSBMalariaVigilance", "orgUnit": "OU", "period": "202611", "value": 4}]}


@pytest.fixture
def run(tmp_path, monkeypatch):
    """A CSB/Malaria run: its context, its two files, the library replaced (it computes, it calls no DHIS2)."""
    monkeypatch.chdir(tmp_path)
    for folder in ("input", "output"):
        (tmp_path / folder).mkdir()
    (tmp_path / "input" / "disease_data.json").write_text(json.dumps({"dataValues": ["history"]}))
    (tmp_path / "input" / "config.json").write_text(json.dumps({"forecast_start": "202611"}))
    (tmp_path / "output" / "forecast.json").write_text(json.dumps({"dataValues": ["forecast"]}))
    context = {"ALERT_NAME": "CSBMalariaVigilance"}
    calls = []
    monkeypatch.setattr(module, "setup_logging", lambda: None)
    monkeypatch.setattr(module, "get_parent_ou", lambda: "OU")
    monkeypatch.setattr(module, "get_ou_level", lambda: "5")
    monkeypatch.setattr(module, "get_disease_code", lambda: "pridec_historic_CSBMalaria")
    monkeypatch.setattr(module.config, "_get", lambda key, default=None: context.get(key, default))
    monkeypatch.setattr(module, "pridec_calc_orgUnit_alerts", lambda **kw: calls.append(kw) or ALERT)
    return tmp_path, context, calls


def test_writes_the_alerts_of_the_run_from_its_own_files_for_the_months_of_its_forecast(run):
    root, _, calls = run

    module.calc_orgunit_alerts()

    assert json.loads((root / "output" / "alerts.json").read_text()) == ALERT  # what post_forecast posts next
    kw = calls[0]
    assert (kw["parent_ou"], kw["ou_level"], kw["disease_code"], kw["alert_name"]) == ("OU", 5, "CSBMalaria", "CSBMalariaVigilance")
    assert (kw["historic_json"], kw["forecast_json"]) == ({"dataValues": ["history"]}, {"dataValues": ["forecast"]})
    assert kw["focal_date"] == date(2026, 11, 1)  # config.json's forecast_start: the months the forecast covers


def test_without_forecast_start_the_current_month_as_the_script(run):
    root, _, calls = run
    (root / "input" / "config.json").write_text(json.dumps({}))

    module.calc_orgunit_alerts()

    assert calls[0]["focal_date"] == date.today()


def test_refuses_a_run_without_alert_and_a_missing_forecast(run):
    root, context, calls = run
    context.pop("ALERT_NAME")  # a COM or ADJ run: no alert
    with pytest.raises(EnvironmentError, match="ALERT_NAME"):
        module.calc_orgunit_alerts()

    context["ALERT_NAME"] = "CSBMalariaVigilance"
    (root / "output" / "forecast.json").unlink()
    with pytest.raises(FileNotFoundError):
        module.calc_orgunit_alerts()
    assert calls == [] and not (root / "output" / "alerts.json").exists()
