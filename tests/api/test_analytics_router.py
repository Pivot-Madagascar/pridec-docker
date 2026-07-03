import pytest
from unittest.mock import MagicMock, patch


def test_build_analytics_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_analytics_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.build_analytics.return_value = "build_analytics_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/build_analytics")
        assert response.status_code == 202


def test_calc_csb_alerts_returns_202(client, mock_task_launcher):
    with patch("etlhub.core.dependencies.get_analytics_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.calc_csb_alerts.return_value = "calc_csb_alerts_abc123"
        mock_get_service.return_value = mock_service
        
        response = client.post("/calc_csb_alerts")
        assert response.status_code == 202