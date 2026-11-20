"""Where the ETL scripts and the forecast get their config: etlhub's version (Redis, login) or the CLI's (.env)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
import redis

from etl.scripts import config
from etlhub import script_config
from etlhub.infrastructure import auth_store, forecast_runner, redis_client
from etlhub.infrastructure.config_store import ConfigStore

CREDENTIAL = {"url": "https://dhis2.test/", "token": "d2pat_login", "pat_uid": "tokenUid001"}
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_etlhub_plugs_its_config_into_the_scripts():
    assert config._get is script_config._get
    assert config._dhis2_credential is script_config._dhis2_credential


def test_scripts_use_the_login_credential(monkeypatch):
    monkeypatch.setattr(auth_store, "get_credential", lambda: CREDENTIAL)
    monkeypatch.setenv("DHIS_TOKEN", "d2pat_from_env")

    assert config.get_dhis_url() == "https://dhis2.test"
    assert config.get_dhis_token() == "d2pat_login"


def test_without_login_etlhub_fails_instead_of_using_env(monkeypatch):
    monkeypatch.setattr(auth_store, "get_credential", lambda: None)
    monkeypatch.setattr(script_config, "_ENV_FALLBACK", False)
    monkeypatch.setenv("DHIS_TOKEN", "d2pat_from_env")

    with pytest.raises(script_config.DHIS2SessionError, match="Log in again"):
        config.get_dhis_token()


def test_env_fallback_uses_env(monkeypatch):
    monkeypatch.setattr(auth_store, "get_credential", lambda: None)
    monkeypatch.setattr(script_config, "_ENV_FALLBACK", True)
    monkeypatch.setenv("DHIS_TOKEN", "d2pat_from_env")

    assert config.get_dhis_token() == "d2pat_from_env"


class _Redis:
    def __init__(self, values=None, down=False):
        self.values, self.down = values or {}, down

    def hget(self, _key, field):
        if self.down:
            raise redis.RedisError("down")
        return self.values.get(field)


def test_editable_keys_come_from_redis_only(monkeypatch):
    monkeypatch.setattr(redis_client, "get_redis", lambda: _Redis({"OU_LEVEL": " 5 "}))
    monkeypatch.setenv("OU_LEVEL", "6")
    monkeypatch.setenv("PARENT_OU", "ou_env")
    monkeypatch.setenv("DRYRUN", "false")
    monkeypatch.setenv("PIVOT_URL", "https://pivot.test")

    assert config.get_ou_level() == "5"
    assert config.get_parent_ou() is None  # absent from Redis: the default, not .env
    assert config.get_dry_run() is True
    assert script_config._get("PIVOT_URL") == "https://pivot.test"  # not editable: the environment


def test_redis_down_fails_the_job_instead_of_using_env(monkeypatch):
    monkeypatch.setattr(redis_client, "get_redis", lambda: _Redis(down=True))
    monkeypatch.setenv("DRYRUN", "false")

    with pytest.raises(redis.RedisError):
        config.get_dry_run()


def test_cli_reads_env_without_etlhub_or_redis(tmp_path):
    """The CLI image has neither etlhub nor redis: config must import and read -e / .env alone."""
    code = (
        "import sys; sys.path.insert(0, 'etl'); import scripts.config as c; "
        "assert not any(m == 'redis' or m.startswith('etlhub') for m in sys.modules), sorted(sys.modules); "
        "assert (c.get_dhis_url(), c.get_dhis_token(), c.get_ou_level()) == ('https://cli.test', 'd2pat_cli', '5'); "
        "assert (c.dryRun, c.DHIS_URL, c.LOG_LEVEL) == (False, 'https://cli.test', 'DEBUG')"
    )
    env = {"PATH": os.environ["PATH"], "DHIS_URL": "https://cli.test/", "DHIS_TOKEN": "d2pat_cli",
           "OU_LEVEL": "5", "DRYRUN": "false", "LOG_LEVEL": "debug"}
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, env=env, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_forecast_env_file_never_contains_dhis2_credentials(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("DHIS_URL=https://env.test\nDHIS_TOKEN=d2pat_env\nOTHER=1\n")
    monkeypatch.setattr(forecast_runner.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(ConfigStore, "get_all", lambda self: {"DHIS_TOKEN": "d2pat_old", "PARENT_OU": "ou1"})

    content = open(forecast_runner._build_dynamic_env_file(str(tmp_path), "job1")).read()

    assert "DHIS_" not in content
    assert "OTHER=1" in content and "PARENT_OU=ou1" in content


def test_a_job_reads_the_configuration_of_its_own_pass_and_its_dhis2(monkeypatch):
    from etlhub.core.job_context import job_pass_config
    monkeypatch.setattr(auth_store, "get_credential", lambda: CREDENTIAL)
    token = job_pass_config.set({"gee_variables": "v1,v2", "parent_ou": "ou_fixed", "log_level": "DEBUG",
                                 "dry_run": True, "dhis_url": CREDENTIAL["url"]})
    try:
        assert (config.get_gee_variables(), config.get_parent_ou(), config.get_log_level()) == (
            ["v1", "v2"], "ou_fixed", "DEBUG")  # never the active pass, Redis or .env
        assert config.get_dhis_token() == "d2pat_login"
        monkeypatch.setattr(auth_store, "get_credential", lambda: {**CREDENTIAL, "url": "https://other.dhis2/"})
        with pytest.raises(script_config.DHIS2SessionError, match="pass runs on https://dhis2.test/"):
            config.get_dhis_token()  # someone logged in to another DHIS2 since the launch
    finally:
        job_pass_config.reset(token)


def test_the_forecast_gets_the_parent_ou_and_log_level_of_its_pass(tmp_path, monkeypatch):
    from etlhub.core.job_context import job_pass_config
    (tmp_path / ".env").write_text("PARENT_OU=ou_env\nLOG_LEVEL=INFO\n")
    monkeypatch.setattr(forecast_runner.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(ConfigStore, "get_all", lambda self: {"PARENT_OU": "ou_redis", "LOG_LEVEL": "INFO"})
    token = job_pass_config.set({"parent_ou": "ou_fixed", "log_level": "DEBUG", "gee_variables": None})
    try:
        content = open(forecast_runner._build_dynamic_env_file(str(tmp_path), "job1")).read()
    finally:
        job_pass_config.reset(token)

    assert "PARENT_OU=ou_fixed" in content and "LOG_LEVEL=DEBUG" in content
    assert "ou_redis" not in content and "ou_env" not in content
