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

class _RecordingLauncher:
    def __init__(self):
        self.launches = []

    def launch(self, task_type, job_id, webhook_url=None, confirm=False, carry_over=None, **kwargs):
        self.launches.append((task_type, carry_over))


def test_an_import_launch_records_its_parameters_and_a_failure_to_read_them_never_blocks_it():
    from etlhub.application.use_cases.ingestion_service import IngestionService
    plan = {"dhis_url": "http://dhis2.test", "imports": [
        {"task": "import_pivot_com", "elements": ["e"], "periods": ["202609"], "org_units": "ou:LEVEL-6;P1"}]}
    launcher = _RecordingLauncher()

    IngestionService(launcher, lambda: plan).launch("import_pivot_com")
    IngestionService(launcher, lambda: plan).launch("fetch_climate")
    IngestionService(launcher, lambda: (_ for _ in ()).throw(EnvironmentError("PARENT_OU missing"))).launch("import_gee")

    assert launcher.launches == [
        ("import_pivot_com", {"import_pivot_com": {"dhis_url": "http://dhis2.test", "task": "import_pivot_com",
                                                   "elements": ["e"], "periods": ["202609"], "org_units": "ou:LEVEL-6;P1"}}),
        ("fetch_climate", None),  # not an import: nothing to record or carry over
        ("import_gee", None),  # launched anyway, without parameters
    ]
