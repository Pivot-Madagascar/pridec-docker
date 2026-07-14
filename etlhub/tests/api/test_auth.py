import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_validate_token_endpoint_exists(client: TestClient):
    """Test that validate-token endpoint exists."""
    response = client.post("/auth/validate-token", json={"token": "test-token"})
    assert response.status_code in [200, 401, 500]


def test_protected_route_requires_auth(client: TestClient):
    """Test that protected routes require authentication."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_missing_credentials_returns_401(client: TestClient):
    """Test that missing Authorization header returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_valid_token_authenticates_user(client: TestClient):
    """Test that a valid token returns user info."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "user123",
        "email": "test@example.com",
        "username": "testuser",
        "displayName": "Test User",
    }

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        with patch("etlhub.api.auth.dhis2_auth.get_settings") as mock_settings:
            mock_settings.return_value.dhis2_url = "http://localhost:8080"
            mock_settings.return_value.dhis2_allowed_hosts = ""
            mock_settings.return_value.dhis2_auth_timeout = 3.0

            response = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer valid-token"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user123"


def test_invalid_token_returns_401(client: TestClient):
    """Test that an invalid token returns 401."""
    mock_response = MagicMock()
    mock_response.status_code = 401

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        with patch("etlhub.api.auth.dhis2_auth.get_settings") as mock_settings:
            mock_settings.return_value.dhis2_url = "http://localhost:8080"
            mock_settings.return_value.dhis2_allowed_hosts = ""
            mock_settings.return_value.dhis2_auth_timeout = 3.0

            response = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer invalid-token"},
            )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired DHIS2 token"


def test_dhis2_unreachable_returns_401(client: TestClient):
    """Test that DHIS2 being unreachable returns 401."""
    import httpx

    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        with patch("etlhub.api.auth.dhis2_auth.get_settings") as mock_settings:
            mock_settings.return_value.dhis2_url = "http://localhost:8080"
            mock_settings.return_value.dhis2_allowed_hosts = ""
            mock_settings.return_value.dhis2_auth_timeout = 3.0

            response = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer some-token"},
            )

    assert response.status_code == 401


def test_invalid_json_response_returns_401(client: TestClient):
    """Test that invalid JSON response from DHIS2 returns 401."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        with patch("etlhub.api.auth.dhis2_auth.get_settings") as mock_settings:
            mock_settings.return_value.dhis2_url = "http://localhost:8080"
            mock_settings.return_value.dhis2_allowed_hosts = ""
            mock_settings.return_value.dhis2_auth_timeout = 3.0

            response = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer some-token"},
            )

    assert response.status_code == 401


def test_token_missing_url_returns_401(client: TestClient):
    """Test that missing DHIS2 URL in settings returns 401."""
    with patch("etlhub.api.auth.dhis2_auth.get_settings") as mock_settings:
        mock_settings.return_value.dhis2_url = ""
        mock_settings.return_value.dhis2_allowed_hosts = ""
        mock_settings.return_value.dhis2_auth_timeout = 3.0

        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer some-token"},
        )

    assert response.status_code == 401


def test_validate_token_endpoint_with_custom_url_returns_user(client: TestClient):
    """Test that validate-token works with custom dhis2_url."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "user456",
        "email": "validate@example.com",
        "username": "validateuser",
        "displayName": "Validate User",
    }

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        with patch("etlhub.api.auth.dhis2_auth.get_settings") as mock_settings:
            mock_settings.return_value.dhis2_url = ""
            mock_settings.return_value.dhis2_allowed_hosts = "localhost:8082"
            mock_settings.return_value.dhis2_auth_timeout = 3.0

            response = client.post(
                "/auth/validate-token",
                json={"token": "valid-token", "dhis2_url": "http://localhost:8082"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert data["user"]["id"] == "user456"


def test_validate_token_endpoint_disallowed_url_returns_400(client: TestClient):
    """Test that validate-token rejects disallowed dhis2_url."""
    with patch("etlhub.api.auth.dhis2_auth.get_settings") as mock_settings:
        mock_settings.return_value.dhis2_url = ""
        mock_settings.return_value.dhis2_allowed_hosts = "trusted.dhis2.com"
        mock_settings.return_value.dhis2_auth_timeout = 3.0

        response = client.post(
            "/auth/validate-token",
            json={"token": "valid-token", "dhis2_url": "http://localhost:8082"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or disallowed DHIS2 URL"


def test_no_credentials_raises_error():
    """Test that missing credentials raises ValueError."""
    from etlhub.api.auth.dhis2_auth import get_dhis2_user_info

    import asyncio
    with patch("etlhub.api.auth.dhis2_auth.get_settings") as mock_settings:
        mock_settings.return_value.dhis2_url = "http://localhost:8080"
        mock_settings.return_value.dhis2_auth_timeout = 3.0

        with pytest.raises(ValueError, match="Authentication required"):
            asyncio.run(get_dhis2_user_info())