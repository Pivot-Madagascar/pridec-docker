"""Editable config: .env loaded into Redis at each API start and on reload, edited from etlui, read by the scripts."""
import pytest
from fastapi.testclient import TestClient

from etl.scripts import config
from etlhub.api.routers import config_router
from etlhub.infrastructure import config_store, redis_client


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
    fake = FakeRedis(PARENT_OU="ou_edited", DISEASE_CODE="old", GEE_VARIABLES="v1")
    monkeypatch.setattr(config_store, "get_redis", lambda: fake)
    monkeypatch.setattr(redis_client, "get_redis", lambda: fake)
    monkeypatch.setattr(config_router, "get_credential", lambda: None)
    env = tmp_path / ".env"
    env.write_text("PARENT_OU=ou_env\nOU_LEVEL='6'\nDRYRUN=True\nDHIS_TOKEN=d2pat_secret\n")
    monkeypatch.setattr(config_store, "ENV_FILE", str(env))
    return fake


def test_load_env_overwrites_and_removes_missing_keys(redis):
    assert config_store.ConfigStore().load_env()

    assert redis == {"PARENT_OU": "ou_env", "OU_LEVEL": "6", "DRYRUN": "True"}  # never DHIS_TOKEN
    assert config.get_disease_code() is None and config._get("GEE_VARIABLES", "") == ""  # removed: the default
    assert (config.get_parent_ou(), config.get_dry_run(), config.get_log_level()) == ("ou_env", True, "INFO")


def test_api_start_loads_env_into_redis(redis, app):
    with TestClient(app):
        assert redis["PARENT_OU"] == "ou_env"


def test_api_does_not_start_on_stale_redis(app, monkeypatch):
    monkeypatch.setattr(config_store.ConfigStore, "load_env", lambda self: False)

    with pytest.raises(RuntimeError, match="is Redis running"):
        with TestClient(app):
            pass


def test_log_level_and_gee_variables_are_editable(redis, client):
    body = client.put("/api/config/", json={"log_level": "DEBUG", "gee_variables": "a_1, b_2"}).json()

    assert (body["log_level"], body["gee_variables"]) == ("DEBUG", "a_1, b_2")
    assert (config.get_log_level(), config.get_gee_variables()) == ("DEBUG", ["a_1", "b_2"])

    client.put("/api/config/", json={"gee_variables": ""})
    assert redis["GEE_VARIABLES"] == ""  # "" = all variables


@pytest.mark.parametrize("payload", [{"log_level": "LOUD"}, {"gee_variables": "a\nDHIS_TOKEN=x"}, {"gee_variables": ",a"}])
def test_invalid_values_are_refused(redis, client, payload):
    assert client.put("/api/config/", json=payload).status_code == 422


def test_reload_uses_the_same_loading(redis, client):
    body = client.put("/api/config/reload").json()

    assert body["parent_ou"] == "ou_env" and body["gee_variables"] is None
