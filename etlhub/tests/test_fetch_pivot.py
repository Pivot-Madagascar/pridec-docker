import json

import pytest

from etlhub.application.use_cases import fetch_pivot as module

ROW = {"period": "202601", "orgUnit": "ou1", "value": 5, "dataElement": "pridec_historic_COMMalaria",
       "categoryOptionCombo": "pridec_COC_u5"}
FLAGGED = {"text": None, "flagged": True, "error": "data is empty"}


@pytest.fixture
def fetched(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = {}

    def com(**kw):
        calls["com"] = kw
        return [{"dataElement": "pridec_historic_COMMalaria", "fetched_data": [ROW],
                 "summary": {"text": "ok", "flagged": False, "error": None}}]

    def csb(**kw):
        calls["csb"] = kw
        return [{"dataElement": "pridec_historic_CSBMalaria", "fetched_data": [], "summary": FLAGGED}]

    monkeypatch.setattr(module, "fetch_pivot_com_etlhub", com)
    monkeypatch.setattr(module, "fetch_pivot_csb_etlhub", csb)
    monkeypatch.setattr(module, "PIVOT_URL", "http://pivot")
    monkeypatch.setattr(module, "PIVOT_TOKEN", "t")
    monkeypatch.setattr(module, "get_parent_ou", lambda: "PASS_OU")
    monkeypatch.setattr(module, "setup_logging", lambda: None)
    return tmp_path, calls


def test_writes_fetched_and_flags_in_the_mode_input_folder(fetched, monkeypatch):
    root, calls = fetched
    module.import_pivot_com()
    module.import_pivot_csb()
    out = root / "input" / "temp_fetch"
    assert json.loads((out / "pridec_historic_COMMalaria_fetched.json").read_text()) == {"dataValues": [ROW]}
    assert json.loads((out / "pridec_historic_CSBMalaria_flags.json").read_text()) == FLAGGED
    assert calls["com"] == {"pivot_token": "t", "pivot_url": "http://pivot", "prior_months": 8, "parent_ou": "PASS_OU"}
    assert "parent_ou" not in calls["csb"]

    monkeypatch.setattr(module, "current_test_mode", lambda: True)
    module.import_pivot_csb()
    assert (root / "test" / "input" / "temp_fetch" / "pridec_historic_CSBMalaria_flags.json").exists()


def test_missing_parent_ou_fails_before_fetching(fetched, monkeypatch):
    _, calls = fetched
    monkeypatch.setattr(module, "get_parent_ou", lambda: None)
    with pytest.raises(EnvironmentError, match="PARENT_OU"):
        module.import_pivot_com()
    assert calls == {}
