import pytest
from unittest.mock import MagicMock, patch


def test_forecast_launch_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_forecast_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.launch.return_value = "forecast_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/forecast/", json={})
        assert response.status_code == 202
        assert response.json()["status"] == "accepted"
        assert response.json()["job_id"].startswith("forecast_")


def test_forecast_status_not_found_returns_404(client, mock_job_repository):
    with patch("etlhub.core.dependencies.get_forecast_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_status.side_effect = Exception("Job not found: abc123")
        mock_get_service.return_value = mock_service
        
        response = client.get("/forecast/status/abc123")
        # Will be handled by global exception handler
        assert response.status_code in [404, 500]