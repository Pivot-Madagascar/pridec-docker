"""Where the ETL scripts and the forecast get DHIS_URL / DHIS_TOKEN."""
import pytest

from etl.scripts import config
from etlhub.infrastructure import forecast_runner
from etlhub.infrastructure.config_store import ConfigStore

CREDENTIAL = {"url": "https://dhis2.test/", "token": "d2pat_login", "pat_uid": "tokenUid001"}


def test_scripts_use_the_login_credential(monkeypatch):
    monkeypatch.setattr(config, "get_credential", lambda: CREDENTIAL)
    monkeypatch.setenv("DHIS_TOKEN", "d2pat_from_env")

    assert config.get_dhis_url() == "https://dhis2.test"
    assert config.get_dhis_token() == "d2pat_login"


def test_without_login_etlhub_fails_instead_of_using_env(monkeypatch):
    monkeypatch.setattr(config, "get_credential", lambda: None)
    monkeypatch.setattr(config, "_ENV_FALLBACK", False)
    monkeypatch.setenv("DHIS_TOKEN", "d2pat_from_env")

    with pytest.raises(config.DHIS2SessionError, match="Log in again"):
        config.get_dhis_token()


def test_cli_falls_back_to_env(monkeypatch):
    monkeypatch.setattr(config, "get_credential", lambda: None)
    monkeypatch.setattr(config, "_ENV_FALLBACK", True)
    monkeypatch.setenv("DHIS_TOKEN", "d2pat_from_env")

    assert config.get_dhis_token() == "d2pat_from_env"


def test_forecast_env_file_never_contains_dhis2_credentials(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("DHIS_URL=https://env.test\nDHIS_TOKEN=d2pat_env\nOTHER=1\n")
    monkeypatch.setattr(forecast_runner.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(ConfigStore, "get_all", lambda self: {"DHIS_TOKEN": "d2pat_old", "PARENT_OU": "ou1"})

    content = open(forecast_runner._build_dynamic_env_file(str(tmp_path), "job1")).read()

    assert "DHIS_" not in content
    assert "OTHER=1" in content and "PARENT_OU=ou1" in content
