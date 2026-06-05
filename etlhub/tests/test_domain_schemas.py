from etlhub.domain.schemas.etl import ETLResponse
from etlhub.domain.schemas.forecast import ForecastParams, JobStatus


def test_etl_response_defaults():
    resp = ETLResponse()
    assert resp.status == ""
    assert resp.message == ""
    assert resp.job_id == ""


def test_etl_response_values():
    resp = ETLResponse(status="accepted", message="ok", job_id="abc")
    assert resp.status == "accepted"
    assert resp.message == "ok"
    assert resp.job_id == "abc"


def test_forecast_params_defaults():
    params = ForecastParams()
    assert params.config_path == "input/config.json"
    assert params.external_data_path == "input/external_data.csv"
    assert params.climate_data_path == "input/climate_data.json"
    assert params.disease_data_path == "input/disease_data.json"
    assert params.orgUnit_poly_path == "input/orgUnit_poly.geojson"


def test_forecast_params_custom():
    params = ForecastParams(config_path="c.json", external_data_path="e.csv")
    assert params.config_path == "c.json"
    assert params.external_data_path == "e.csv"


def test_job_status_success():
    status = JobStatus(status="success", job_id="j1", logs="log data")
    assert status.status == "success"
    assert status.job_id == "j1"
    assert status.logs == "log data"


def test_job_status_defaults():
    status = JobStatus(status="error", job_id="j2")
    assert status.started is None
    assert status.completed is None
    assert status.logs is None
    assert status.message is None
