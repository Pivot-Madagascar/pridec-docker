import pytest
from unittest.mock import MagicMock


def test_import_gee_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app

    client = TestClient(app)
    response = client.post("/import_gee")
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data


def test_import_pivot_com_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.post("/import_pivot_com")
    assert response.status_code == 202


def test_import_pivot_csb_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.post("/import_pivot_csb")
    assert response.status_code == 202


def test_fetch_climate_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.post("/fetch_climate")
    assert response.status_code == 202


def test_fetch_disease_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.post("/fetch_disease")
    assert response.status_code == 202


def test_fetch_geojson_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.post("/fetch_geojson")
    assert response.status_code == 202