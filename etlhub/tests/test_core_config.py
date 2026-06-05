from unittest.mock import patch, MagicMock

from etlhub.core.config import Settings, get_settings


def test_get_settings_returns_settings():
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_settings_defaults():
    settings = Settings()
    assert settings.host_pwd == "."
    assert settings.logs_dir == "logs"
    assert settings.data_dir == "."


@patch.dict("os.environ", {"HOST_PWD": "/tmp", "logs_dir": "mylogs"})
def test_settings_from_env():
    settings = Settings()
    assert settings.host_pwd == "/tmp"
    assert settings.logs_dir == "mylogs"


def test_get_settings_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
