from fastapi.testclient import TestClient


def test_list_requests_returns_list(override_dependencies):
    response = TestClient(override_dependencies).get("/api/tracking/requests")

    assert response.status_code == 200
    assert response.json() == []


def test_get_request_not_found_returns_404(override_dependencies):
    response = TestClient(override_dependencies).get("/api/tracking/requests/abc123")

    assert response.status_code == 404
    assert response.json() == {"message": "Job not found"}


def test_get_etl_logs_not_found_returns_404(override_dependencies):
    response = TestClient(override_dependencies).get("/api/tracking/etl-logs/abc123")

    assert response.status_code == 404
    assert response.json() == {"message": "Job not found"}


def test_list_requests_filters_by_endpoint(override_dependencies, mock_request_tracker):
    calls = []
    mock_request_tracker.list_recent = lambda *args: calls.append(args) or []

    response = TestClient(override_dependencies).get("/api/tracking/requests?endpoint=/api/ingest")

    assert response.status_code == 200
    assert calls == [(50, "/api/ingest", "production")]  # limit, endpoint, the mode served
