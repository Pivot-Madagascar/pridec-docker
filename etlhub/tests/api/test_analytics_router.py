import pytest
from unittest.mock import MagicMock


def test_build_analytics_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.post("/build_analytics")
    assert response.status_code == 202


def test_inline_scripts_run_off_the_event_loop():
    """An async def handler calling the synchronous service would freeze the whole API while the script runs."""
    import inspect
    from etlhub.api.routers.etl.analytics_router import api_update_key

    assert not inspect.iscoroutinefunction(api_update_key)


def test_post_forecast_is_a_background_job(override_dependencies):
    """Since 2026-11-24 a Celery job (was synchronous): 202 at once, its job_id followed by etlui's toast."""
    from fastapi.testclient import TestClient
    from etlhub.main import app

    response = TestClient(app).post("/post_forecast")
    assert response.status_code == 202
    assert response.json()["job_id"].startswith("post_forecast_")


def test_calc_csb_alerts_is_no_longer_a_route(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app

    assert TestClient(app).post("/calc_csb_alerts").status_code == 404


def test_list_requests(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app
    
    client = TestClient(app)
    response = client.get("/api/tracking/requests")
    assert response.status_code == 200
    assert response.json() == []


def test_home_endpoint(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"