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