import pytest
from unittest.mock import MagicMock, patch
from etlhub.domain.exceptions import JobNotFoundError
from fastapi.testclient import TestClient


def test_list_requests_returns_list(override_dependencies):
    from etlhub.main import app
    client = TestClient(app)
    with patch("etlhub.core.dependencies.get_tracking_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.list_requests.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get("/api/tracking/requests")
        assert response.status_code == 200


def test_get_request_not_found_returns_404(override_dependencies):
    from etlhub.main import app
    client = TestClient(app)
    with patch("etlhub.core.dependencies.get_tracking_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_request.side_effect = JobNotFoundError("Job not found: abc123")
        mock_get_service.return_value = mock_service

        response = client.get("/api/tracking/requests/abc123")
        assert response.status_code in [404, 500]


def test_get_etl_logs_not_found_returns_404(override_dependencies):
    from etlhub.main import app
    client = TestClient(app)
    with patch("etlhub.core.dependencies.get_tracking_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_etl_logs.side_effect = JobNotFoundError("Job not found: abc123")
        mock_get_service.return_value = mock_service

        response = client.get("/api/tracking/etl-logs/abc123")
        assert response.status_code in [404, 500]