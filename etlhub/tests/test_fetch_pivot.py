import pytest

from etlhub.application.use_cases import fetch_pivot as module

ROW = {"period": "202601", "orgUnit": "ou1", "value": 5, "dataElement": "pridec_historic_COMMalaria",
       "categoryOptionCombo": "pridec_COC_u5"}
FLAGGED = {"text": None, "flagged": True, "error": "data is empty"}


class _Store:  # the FetchedImports port, in memory (infrastructure/fetched_imports.py: Redis, per pass and mode)
    def __init__(self):
        self.data = {}

    def save(self, task, items):
        self.data[task] = items

    def load(self, task):
        return self.data.get(task, [])


@pytest.fixture
def fetched(monkeypatch):
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
    monkeypatch.setattr(module, "pivot_url", lambda: "http://pivot")
    monkeypatch.setattr(module, "PIVOT_TOKEN", "t")
    monkeypatch.setattr(module, "get_parent_ou", lambda: "PASS_OU")
    monkeypatch.setattr(module, "setup_logging", lambda: None)
    store = _Store()
    return store, calls


def test_nothing_fetched_lists_every_import_empty(fetched):
    store, _ = fetched
    assert module.fetched_imports(store) == [{"task": "import_pivot_com", "elements": []},
                                        {"task": "import_pivot_csb", "elements": []}]


def test_each_import_keeps_its_answer_and_the_same_import_again_replaces_it_whole(fetched, monkeypatch):
    store, calls = fetched
    module.import_pivot_com(store)
    module.import_pivot_csb(store)

    assert module.fetched_imports(store) == [
        {"task": "import_pivot_com", "elements": [{"data_element": "pridec_historic_COMMalaria", "rows": 1,
                                                   "flagged": False, "text": "ok", "error": None,
                                                   "post": None}]},
        {"task": "import_pivot_csb", "elements": [{"data_element": "pridec_historic_CSBMalaria", "rows": 0,
                                                   "flagged": True, "text": None, "error": "data is empty",
                                                   "post": None}]}]
    assert store.data["import_pivot_com"][0]["fetched_data"] == [ROW]  # what the approval posts
    assert calls["com"] == {"pivot_token": "t", "pivot_url": "http://pivot", "prior_months": 8, "parent_ou": "PASS_OU"}
    assert "parent_ou" not in calls["csb"]

    monkeypatch.setattr(module, "fetch_pivot_com_etlhub", lambda **kw: [])  # COM again: nothing this time
    module.import_pivot_com(store)
    assert module.fetched_imports(store)[0] == {"task": "import_pivot_com", "elements": []}
    assert module.fetched_imports(store)[1]["elements"]  # CSB untouched


def test_missing_parent_ou_fails_before_fetching(fetched, monkeypatch):
    store, calls = fetched
    monkeypatch.setattr(module, "get_parent_ou", lambda: None)
    with pytest.raises(EnvironmentError, match="PARENT_OU"):
        module.import_pivot_com(store)
    assert calls == {}
