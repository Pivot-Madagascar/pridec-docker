import pytest
from unittest.mock import MagicMock, patch


def test_import_gee_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_ingestion_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.import_gee.return_value = "import_gee_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/import_gee")
        assert response.status_code == 202
        assert response.json()["status"] == "accepted"
        assert response.json()["job_id"].startswith("import_gee_")


def test_import_pivot_com_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_ingestion_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.import_pivot_com.return_value = "import_pivot_com_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/import_pivot_com")
        assert response.status_code == 202


def test_import_pivot_csb_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_ingestion_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.import_pivot_csb.return_value = "import_pivot_csb_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/import_pivot_csb")
        assert response.status_code == 202


def test_fetch_climate_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_ingestion_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.fetch_climate.return_value = "fetch_climate_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/fetch_climate")
        assert response.status_code == 202


def test_fetch_disease_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_ingestion_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.fetch_disease.return_value = "fetch_disease_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/fetch_disease")
        assert response.status_code == 202


def test_fetch_geojson_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_ingestion_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.fetch_geojson.return_value = "fetch_geojson_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/fetch_geojson")
        assert response.status_code == 202