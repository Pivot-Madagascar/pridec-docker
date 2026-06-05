import sys
import types
from unittest.mock import patch, MagicMock
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient


for _mod, _attrs in {
    "pridec_gee": ["AVAILABLE_VARIABLES"],
    "pivot_dhis_tools": [],
    "etl.scripts.import_gee": ["import_gee"],
    "etl.scripts.import_pivot_COM": ["import_pivot_com"],
    "etl.scripts.import_pivot_CSB": ["import_pivot_csb"],
    "etl.scripts.fetch_pridec_climate": ["fetch_climate"],
    "etl.scripts.fetch_pridec_disease": ["fetch_disease"],
    "etl.scripts.fetch_pridec_geojson": ["fetch_geojson"],
    "etl.scripts.build_analytics": ["build_analytics"],
    "etl.scripts.post_forecast": ["post_forecast"],
    "etl.scripts.calc_CSB_alerts": ["calc_csb_alerts"],
    "etl.scripts.update_pridec_key": ["update_key"],
}.items():
    m = types.ModuleType(_mod)
    for _attr in _attrs:
        setattr(m, _attr, lambda *a, **k: None)
    sys.modules.setdefault(_mod, m)


from etlhub.main import app

client = TestClient(app)


def _mock_start_forecast(*args, **kwargs):
    from etlhub.domain.schemas import ETLResponse
    return ETLResponse(status="accepted", message="Forecast started", job_id="job_123")


@patch(
    "etlhub.api.routers.forecast_router.start_forecast",
    side_effect=_mock_start_forecast,
)
@patch(
    "etlhub.api.routers.forecast_router.get_job_store",
    return_value=None,
)
def test_forecast_endpoint(*_):
    payload = {
        "config_path": "input/config.json",
        "external_data_path": "input/external_data.csv",
        "climate_data_path": "input/climate_data.json",
        "disease_data_path": "input/disease_data.json",
        "orgUnit_poly_path": "input/orgUnit_poly.geojson",
    }
    resp = client.post("/forecast/", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["job_id"] == "job_123"


@patch(
    "etlhub.api.routers.forecast_router.get_job_store",
    return_value=None,
)
def test_forecast_status_returns_404_when_missing(_):
    resp = client.get("/forecast/status/missing")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Job not found"

