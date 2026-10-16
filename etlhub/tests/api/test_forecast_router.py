import pytest
from unittest.mock import MagicMock


def test_forecast_launch_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    from etlhub.domain.schemas.forecast import ForecastParams
    
    client = TestClient(app)
    response = client.post("/forecast/", json={})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data


def test_forecast_status_endpoint(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.get("/forecast/status/test123")
    assert response.status_code in [200, 404]

def test_forecast_launch_forwards_webhook_url(app, mock_job_repository, monkeypatch):
    from fastapi.testclient import TestClient
    from etlhub.core.config import get_settings
    from etlhub.core.dependencies import get_forecast_service
    from etlhub.application.use_cases.forecast_service import ForecastService

    launched = []

    class SpyTaskLauncher:
        def launch(self, task_type, job_id, webhook_url=None, **kwargs):
            launched.append((task_type, webhook_url))

    monkeypatch.setattr(get_settings(), "webhook_allowed_hosts", "hook.example")
    app.dependency_overrides[get_forecast_service] = lambda: ForecastService(SpyTaskLauncher(), mock_job_repository)
    try:
        response = TestClient(app).post("/forecast/?webhook_url=https://hook.example/cb", json={})
    finally:
        app.dependency_overrides.pop(get_forecast_service, None)

    assert response.status_code == 202
    assert response.json()["webhook_url"] == "https://hook.example/cb"
    assert launched == [("forecast", "https://hook.example/cb")]


@pytest.mark.parametrize("field", ["config_valid_path", "input_valid_path", "polygon_valid_path"])
@pytest.mark.parametrize("bad_path", ["../x.json", "input/../../x.json", "/etc/passwd", "--help", "output/x.json", "input/", ""])
def test_forecast_rejects_paths_outside_input(override_dependencies, field, bad_path):
    from fastapi.testclient import TestClient

    response = TestClient(override_dependencies).post("/forecast/", json={field: bad_path})

    assert response.status_code == 422


def test_forecast_accepts_nested_input_path(override_dependencies):
    from fastapi.testclient import TestClient

    response = TestClient(override_dependencies).post("/forecast/", json={"input_valid_path": "input/run1/input_valid.json"})

    assert response.status_code == 202
