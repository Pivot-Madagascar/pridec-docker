import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(override_dependencies, monkeypatch):
    from etlhub.core.config import get_settings
    from etlhub.main import app
    monkeypatch.setattr(get_settings(), "webhook_allowed_hosts", "hook.example")
    return TestClient(app)


@pytest.mark.parametrize("route", ["/import_gee", "/validate_inputs", "/forecast/"])
@pytest.mark.parametrize("url", [
    "http://hook.example/cb",        # not https
    "https://127.0.0.1/cb",          # host not allowed
    "https://hook.example.evil/cb",  # suffix of an allowed host
    "file:///etc/passwd",
])
def test_launch_rejects_webhook_outside_allow_list(client, route, url):
    response = client.post(route, params={"webhook_url": url}, json={})
    assert response.status_code == 422


def test_empty_allow_list_refuses_every_webhook(client, monkeypatch):
    from etlhub.core.config import get_settings
    monkeypatch.setattr(get_settings(), "webhook_allowed_hosts", "")
    assert client.post("/import_gee", params={"webhook_url": "https://hook.example/cb"}).status_code == 422


def test_launch_accepts_allowed_webhook_and_no_webhook(client):
    assert client.post("/import_gee", params={"webhook_url": "https://hook.example/cb"}).status_code == 202
    assert client.post("/import_gee").status_code == 202


@pytest.mark.parametrize("param", ["config_path", "disease_data_path", "input_dir"])
@pytest.mark.parametrize("bad_path", ["/etc/passwd", "input/../../x", "output/x.json", "--help", "input"])
def test_validate_inputs_rejects_paths_outside_input(client, param, bad_path):
    assert client.post("/validate_inputs", params={param: bad_path}).status_code == 422


def test_validate_inputs_accepts_paths_under_input(client):
    response = client.post("/validate_inputs", params={"input_dir": "input/run1", "config_path": "input/run1/config.json"})
    assert response.status_code == 202
