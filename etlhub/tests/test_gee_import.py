import pytest

from etlhub.application.use_cases import gee_import as module


class _Store:  # the FetchedImports port, in memory (infrastructure/fetched_imports.py: Redis, per pass and mode)
    def __init__(self):
        self.data = {}

    def save(self, task, items):
        self.data[task] = items

    def load(self, task):
        return self.data.get(task, [])


class _Ok:  # DHIS2's answer to a post
    def json(self):
        return {"status": "OK", "response": {"status": "SUCCESS", "importCount": {"imported": 1}}}


def _row(name):
    return {"orgUnit": "ou1", "period": "202610", "value": 1.5, "dataElement": name}


@pytest.fixture
def job(monkeypatch):
    """The job with GEE and DHIS2 replaced: a fetch returning `rows`, posts recorded."""
    store, posts, rows = _Store(), [], {"value": []}
    monkeypatch.setattr(module, "setup_logging", lambda: None)
    monkeypatch.setattr(module, "get_gee_variables", lambda: ["a_1", "b_2", "c_3"])
    monkeypatch.setattr(module, "get_dhis_url", lambda: "https://dhis2.test")
    monkeypatch.setattr(module, "get_dhis_token", lambda: "t")
    monkeypatch.setattr(module, "get_parent_ou", lambda: "OU")
    monkeypatch.setattr(module, "get_dry_run", lambda: True)
    monkeypatch.setattr(module, "GEE_SERVICE_ACCOUNT", "sa@gee")
    monkeypatch.setattr(module, "_fetch", lambda variables, url, token, parent_ou: rows["value"])

    def post(base_url, payload, token, dryRun):
        posts.append([r["dataElement"] for r in payload["dataValues"]])
        if payload["dataValues"][0]["dataElement"] == "b_2":
            raise RuntimeError("500 Server Error")
        return _Ok()

    monkeypatch.setattr(module, "post_climate", post)
    return store, posts, rows


def _states(store):
    return {s["variable"]: (s["status"], s["rows"], s["error"]) for s in store.load("import_gee")}


def test_one_fetch_then_one_post_per_chosen_variable_with_its_values_only(job):
    store, posts, rows = job
    # pridec_gee returns every variable of a source when one is asked: z_9 was not chosen, never posted
    rows["value"] = [_row("a_1"), _row("a_1"), _row("z_9"), _row("b_2"), _row("c_3")]

    with pytest.raises(RuntimeError, match="GEE import failed for b_2"):
        module.import_gee(store)

    assert posts == [["a_1", "a_1"], ["b_2"], ["c_3"]]  # b_2 failed, c_3 still posted (independent variables)
    assert _states(store) == {"a_1": ("imported", 2, None), "b_2": ("failed", None, "500 Server Error"),
                              "c_3": ("imported", 1, None)}
    assert all(s["dry_run"] is True for s in store.load("import_gee"))


def test_a_variable_without_values_is_empty_and_the_job_succeeds(job):
    store, posts, rows = job
    rows["value"] = [_row("a_1"), _row("c_3")]
    module.get_gee_variables = lambda: ["a_1", "c_3"]  # monkeypatched by the fixture: restored after the test

    module.import_gee(store)

    assert _states(store) == {"a_1": ("imported", 1, None), "c_3": ("imported", 1, None)}

    rows["value"] = [_row("a_1")]
    module.import_gee(store)
    assert _states(store)["c_3"] == ("empty", 0, None)


def test_a_failed_fetch_fails_every_chosen_variable(job, monkeypatch):
    store, posts, _ = job

    def fetch(*args):
        raise RuntimeError("GEE quota")

    monkeypatch.setattr(module, "_fetch", fetch)
    with pytest.raises(RuntimeError, match="GEE quota"):
        module.import_gee(store)

    assert posts == []
    assert {v: s[0] for v, s in _states(store).items()} == {"a_1": "failed", "b_2": "failed", "c_3": "failed"}
    assert "GEE quota" in _states(store)["a_1"][2]


def test_the_list_has_every_variable_whether_the_pass_imports_it_and_its_last_state(job, monkeypatch):
    store, _, rows = job
    monkeypatch.setattr(module, "available_gee_variables", lambda: ["a_1", "b_2", "c_3"])
    assert [(v["variable"], v["chosen"], v["state"]) for v in module.gee_imports(store, None)] == [
        ("a_1", True, None), ("b_2", True, None), ("c_3", True, None)]  # a pass without a choice imports them all

    rows["value"] = [_row("a_1")]
    module.get_gee_variables = lambda: ["a_1"]
    module.import_gee(store)

    listed = module.gee_imports(store, "a_1,c_3")
    assert [(v["variable"], v["chosen"]) for v in listed] == [("a_1", True), ("b_2", False), ("c_3", True)]
    assert listed[0]["state"]["status"] == "imported"
    assert listed[2]["state"] is None  # chosen now, not imported yet
