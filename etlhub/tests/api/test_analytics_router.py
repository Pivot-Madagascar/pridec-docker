import pytest
from unittest.mock import MagicMock


def test_build_analytics_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.post("/build_analytics")
    assert response.status_code == 202


def test_calc_csb_alerts_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.post("/calc_csb_alerts")
    assert response.status_code == 202


def test_list_requests(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.get("/api/tracking/requests")
    assert response.status_code == 200
    assert response.json() == []


def test_home_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200