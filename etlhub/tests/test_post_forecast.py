import json
from types import SimpleNamespace

import pytest

from etlhub.application.use_cases import post_forecast as module


@pytest.fixture
def posted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output").mkdir()
    calls = []
    monkeypatch.setattr(module, "post_dataElements", lambda **kw: calls.append(kw["payload"]))
    monkeypatch.setattr(module, "get_dhis_url", lambda: "http://dhis")
    monkeypatch.setattr(module, "get_dhis_token", lambda: "t")
    monkeypatch.setattr(module, "get_dry_run", lambda: True)
    monkeypatch.setattr(module, "setup_logging", lambda: None)
    alert_name = {"ALERT_NAME": None}  # a COM/ADJ run by default; tests set a CSB run's
    monkeypatch.setattr(module, "config", SimpleNamespace(_get=lambda key: alert_name.get(key)))
    return tmp_path / "output", calls, alert_name


def test_posts_forecast_then_alerts(posted):
    out, calls, _ = posted
    (out / "forecast.json").write_text(json.dumps({"f": 1}))
    (out / "alerts.json").write_text(json.dumps({"a": 1}))
    assert module.post_forecast() == "Forecast and alerts posted"
    assert calls == [{"f": 1}, {"a": 1}]


def test_alerts_are_optional_forecast_is_not(posted):
    out, calls, alert_name = posted
    with pytest.raises(FileNotFoundError):
        module.post_forecast()
    (out / "forecast.json").write_text(json.dumps({"f": 1}))
    assert module.post_forecast() == "Forecast posted"  # a COM/ADJ run: no alerts to miss
    assert calls == [{"f": 1}]

    alert_name["ALERT_NAME"] = "CSBMalariaVigilance"  # a CSB run without alerts.json: the end message says so
    assert module.post_forecast() == (
        "Forecast posted; the alert data was not included (no alerts.json: alerts skipped or not computed)")
