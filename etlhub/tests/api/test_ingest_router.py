import pytest


@pytest.fixture
def launches(override_dependencies, mock_task_launcher, monkeypatch):
    """The launcher calls of the IngestionService the routes get: (task_type, job_id, keyword arguments)."""
    calls = []
    monkeypatch.setattr(mock_task_launcher, "launch",
                        lambda task_type, job_id, **kwargs: calls.append((task_type, job_id, kwargs)))
    return calls


@pytest.mark.parametrize(
    "task", ["import_gee", "import_pivot_com", "import_pivot_csb", "fetch_climate", "fetch_disease", "fetch_geojson"])
def test_a_launch_returns_202_with_the_job_id_it_queued(override_dependencies, launches, task):
    from fastapi.testclient import TestClient

    response = TestClient(override_dependencies).post(f"/{task}", params={"confirm": "true"})

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["job_id"].startswith(f"{task}_")
    assert [(t, j, k["confirm"], k["webhook_url"]) for t, j, k in launches] == [(task, data["job_id"], True, None)]


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

    IngestionService(launcher, None, lambda settings: plan).launch("import_pivot_com")
    IngestionService(launcher, None, lambda settings: plan).launch("fetch_climate")
    IngestionService(launcher, None, lambda settings: (_ for _ in ()).throw(EnvironmentError("PARENT_OU missing"))).launch("import_gee")

    assert launcher.launches == [
        ("import_pivot_com", {"import_pivot_com": {"dhis_url": "http://dhis2.test", "task": "import_pivot_com",
                                                   "elements": ["e"], "periods": ["202609"], "org_units": "ou:LEVEL-6;P1"}}),
        ("fetch_climate", None),  # not an import: nothing to record or carry over
        ("import_gee", None),  # launched anyway, without parameters
    ]


def test_calc_orgunit_alerts_returns_202(override_dependencies):
    from fastapi.testclient import TestClient
    from etlhub.main import app

    response = TestClient(app).post("/calc_orgunit_alerts")
    assert response.status_code == 202
    assert response.json()["job_id"].startswith("calc_orgunit_alerts_")
