"""The Pivot imports' last fetch in Redis: one key per import, pass and mode (Redis and the store faked)."""
from types import SimpleNamespace

from etlhub.core.job_context import pipeline_test_mode
from etlhub.infrastructure import fetched_imports as module


def test_one_key_per_import_pass_and_mode(monkeypatch):
    data = {}
    monkeypatch.setattr(module, "get_redis", lambda: SimpleNamespace(get=data.get, set=data.__setitem__))
    shown = {"pass": {"id": "p1"}}
    monkeypatch.setattr(module, "get_checkpoint_store", lambda: SimpleNamespace(progress=lambda: shown))
    store = module.RedisFetchedImports()
    token = pipeline_test_mode.set(False)
    try:
        store.save("import_pivot_com", [{"dataElement": "x", "fetched_data": [{"period": "202601"}]}])
        assert store.load("import_pivot_com") == [{"dataElement": "x", "fetched_data": [{"period": "202601"}]}]
        assert store.load("import_pivot_csb") == []  # never fetched in this pass
        shown["pass"] = {"id": "p2"}
        assert store.load("import_pivot_com") == []  # a new pass starts empty
        shown["pass"] = {"id": "p1"}
        assert store.load("import_pivot_com")  # back to that pass (resumed): its fetch is still there
        pipeline_test_mode.set(True)
        assert store.load("import_pivot_com") == []  # the other mode never sees it
    finally:
        pipeline_test_mode.reset(token)
    assert list(data) == ["pivot_fetched:production:p1:import_pivot_com"]
