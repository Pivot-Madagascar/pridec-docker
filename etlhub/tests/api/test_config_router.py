"""Editable config: .env loaded into Redis at each API start and on reload, edited from etlui, read by the scripts."""
import sys

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

    assert redis == {"PARENT_OU": "ou_env", "OU_LEVEL": "6", "DRYRUN": "True"}  # never DHIS_TOKEN
    assert config.get_disease_code() is None  # removed: the default
    assert (config.get_parent_ou(), config.get_dry_run(), config.get_log_level()) == ("ou_env", True, "INFO")


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
