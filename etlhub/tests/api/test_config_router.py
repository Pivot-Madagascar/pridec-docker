"""Editable config: .env loaded into Redis at each API start and on reload, edited from etlui, read by the scripts."""
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from etl.scripts import config
from etlhub.infrastructure import auth_store, config_store, redis_client


class FakeRedis(dict):
    def hgetall(self, _key):
        return dict(self)

    def hget(self, _key, field):
        return self.get(field)

    def hset(self, _key, mapping):
        assert mapping, "redis refuses an empty mapping"
        self.update(mapping)

    def hdel(self, _key, *fields):
        for f in fields:
            self.pop(f, None)


@pytest.fixture
def redis(tmp_path, monkeypatch):
    fake = FakeRedis(PARENT_OU="ou_edited", DISEASE_CODE="old")
    monkeypatch.setattr(sys.modules["pridec_gee"], "AVAILABLE_VARIABLES", ["a_1", "b_2", "c_3"])  # a MagicMock here
    monkeypatch.setattr(config_store, "get_redis", lambda: fake)
    monkeypatch.setattr(redis_client, "get_redis", lambda: fake)
    monkeypatch.setattr(auth_store, "get_credential", lambda: None)
    env = tmp_path / ".env"
    env.write_text("PARENT_OU=ou_env\nOU_LEVEL='6'\nDRYRUN=True\nDHIS_TOKEN=d2pat_secret\n")
    monkeypatch.setattr(config_store, "ENV_FILE", str(env))
    return fake


def test_load_env_overwrites_and_removes_missing_keys(redis):
    assert config_store.ConfigStore().load_env()

    assert redis == {"PARENT_OU": "ou_env", "OU_LEVEL": "6"}  # never DHIS_TOKEN; DRYRUN is the CLI's only
    assert config.get_disease_code() is None  # removed: the default
    assert (config.get_parent_ou(), config.get_dry_run(), config.get_log_level()) == ("ou_env", False, "INFO")
    # DRYRUN=True of .env ignored: production mode, DRYRUN = TEST MODE = false


def test_api_start_loads_env_into_redis(redis, app):
    with TestClient(app):
        assert redis["PARENT_OU"] == "ou_env"


def test_api_does_not_start_on_stale_redis(app, monkeypatch):
    monkeypatch.setattr(config_store.ConfigStore, "load_env", lambda self: False)

    with pytest.raises(RuntimeError, match="is Redis running"):
        with TestClient(app):
            pass


def test_log_level_is_editable_and_gee_variables_are_pridec_gee_s_read_only(redis, client):
    body = client.put("/api/config/", json={"log_level": "DEBUG", "gee_variables": "a_1"}).json()

    assert (body["log_level"], body["gee_variables"]) == ("DEBUG", ["a_1", "b_2", "c_3"])
    assert config.get_log_level() == "DEBUG" and "GEE_VARIABLES" not in redis  # ignored: a pass chooses its own


def test_the_scripts_read_the_active_pass_s_gee_variables_never_env_nor_redis(redis, checkpoint_store, monkeypatch):
    monkeypatch.setenv("GEE_VARIABLES", "from_env")
    redis["GEE_VARIABLES"] = "from_redis"  # left by an etlhub from before 2026-11-20

    assert config.get_gee_variables() == ["a_1", "b_2", "c_3"]  # no active pass: all of them
    checkpoint_store.start_pass(gee_variables="b_2,c_3")
    assert config.get_gee_variables() == ["b_2", "c_3"]


def test_the_scripts_read_the_open_run_s_context_written_at_its_launch(redis, monkeypatch):
    """calc_orgunit_alerts failed with 'ALERT_NAME is missing' (2026-11-24): the launch wrote it to Redis, _get read the
    environment for it (not an editable key)."""
    from etlhub.domain.pipeline import run_context
    from etlhub.infrastructure.checkpoint_store import apply_to_config_store
    monkeypatch.setenv("ALERT_NAME", "from_env")  # never read under etlhub: the run's, in Redis

    apply_to_config_store(run_context("CSB/Malaria"))
    assert (config.get_disease_code(), config.get_ou_level(), config._get("ALERT_NAME")) == (
        "pridec_historic_CSBMalaria", "5", "CSBMalariaVigilance")
    apply_to_config_store(run_context("COM/Malaria"))  # no alert in a COM run: the key is removed
    assert config._get("ALERT_NAME") is None


def test_pivot_url_comes_from_the_config_and_the_token_never_leaves_the_environment(redis, client, monkeypatch):
    from etlhub.application.use_cases import fetch_pivot
    monkeypatch.setenv("PIVOT_URL", "https://from-env.test")  # ignored under etlhub: Redis only
    monkeypatch.setattr(fetch_pivot, "PIVOT_TOKEN", "pivot_secret")

    body = client.put("/api/config/", json={"pivot_url": "https://pivot.test/"}).json()

    assert (body["pivot_url"], body["has_pivot_token"]) == ("https://pivot.test/", True)
    assert "pivot_secret" not in str(body) and "PIVOT_TOKEN" not in redis
    assert fetch_pivot.pivot_url() == "https://pivot.test"  # what the import jobs use


@pytest.mark.parametrize("payload", [{"log_level": "LOUD"}, {"ou_level": 0}, {"pivot_url": "pivot.test"}])
def test_invalid_values_are_refused(redis, client, payload):
    assert client.put("/api/config/", json=payload).status_code == 422


def test_reload_uses_the_same_loading(redis, client):
    body = client.put("/api/config/reload").json()

    assert body["parent_ou"] == "ou_env" and body["gee_variables"] == ["a_1", "b_2", "c_3"]


def test_the_routes_get_their_stores_by_injection(redis, app, client):
    """Depends in the route signatures (etlhub/CLAUDE.md, Architecture): app.dependency_overrides reaches every route."""
    from etlhub.core.dependencies import get_auth_store, get_config_store

    class Store:
        data = {"PARENT_OU": "ou_fake"}

        def get_all(self):
            return dict(self.data)

        def set_all(self, config):
            self.data = {**self.data, **config}
            return True

        def load_env(self):
            return False  # the real one succeeds on the fixture's .env

    store = Store()
    app.dependency_overrides[get_config_store] = lambda: store
    app.dependency_overrides[get_auth_store] = lambda: SimpleNamespace(get_credential=lambda: {"token": "t"})
    try:
        assert client.get("/api/config/").json()["parent_ou"] == "ou_fake"  # the real store holds ou_edited
        body = client.put("/api/config/", json={"log_level": "DEBUG"}).json()
        assert (body["log_level"], body["has_dhis_token"]) == ("DEBUG", True) and "LOG_LEVEL" not in redis
        assert client.put("/api/config/reload").status_code == 502
    finally:
        app.dependency_overrides.pop(get_config_store, None)
        app.dependency_overrides.pop(get_auth_store, None)
