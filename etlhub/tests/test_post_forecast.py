import json

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
    return tmp_path / "output", calls


def test_posts_forecast_then_alerts(posted):
    out, calls = posted
    (out / "forecast.json").write_text(json.dumps({"f": 1}))
    (out / "alerts.json").write_text(json.dumps({"a": 1}))
    module.post_forecast()
    assert calls == [{"f": 1}, {"a": 1}]


def test_alerts_are_optional_forecast_is_not(posted):
    out, calls = posted
    with pytest.raises(FileNotFoundError):
        module.post_forecast()
    (out / "forecast.json").write_text(json.dumps({"f": 1}))
    module.post_forecast()
    assert calls == [{"f": 1}]
