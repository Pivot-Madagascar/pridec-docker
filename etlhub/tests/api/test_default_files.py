"""Default input files: read from assets/, offered per mode, used in the open run (real gate, temporary db)."""
import json

import pytest
from fastapi.testclient import TestClient

from etlhub.infrastructure.default_files import ASSETS, SOURCES, DefaultFiles
from tests.infrastructure.test_checkpoint_store import _import

TEST_SOURCES = {
    "production": {"config/Malaria": "prod/config_malaria.json", "external_data/fkt": "prod/external_data_fkt.csv"},
    "test": {"config/Malaria": "test/config.json", "external_data/fkt": "test/external_data.csv"},
}


@pytest.fixture
def assets(tmp_path):
    root = tmp_path / "assets"
    for folder in ("prod", "test"):
        (root / folder).mkdir(parents=True)
    (root / "prod/config_malaria.json").write_text('{"model": "prod"}')
    (root / "prod/external_data_fkt.csv").write_text("orgUnit,period,x\nOU1,202401,1\n")
    (root / "test/config.json").write_text('{"model": "test"}')
    (root / "test/external_data.csv").write_text("orgUnit,period,x\nOU2,202401,2\n")
    return root


@pytest.fixture
def defaults(assets):
    return DefaultFiles(assets, TEST_SOURCES)


@pytest.fixture
def client(app, tmp_path, defaults):
    from etlhub.core.dependencies import get_input_upload_service, get_pipeline_gate
    from etlhub.application.use_cases.input_upload_service import InputUploadService

    app.dependency_overrides[get_input_upload_service] = (
        lambda: InputUploadService(tmp_path / "input", get_pipeline_gate(), defaults))
    yield TestClient(app)
    app.dependency_overrides.pop(get_input_upload_service)


def test_a_missing_file_is_not_offered(assets, defaults):
    (assets / "test/config.json").unlink()

    assert "config/Malaria" not in defaults.current("test")
    assert defaults.path("test", "config/Malaria") is None


def test_every_repo_default_exists():
    """The real mapping points to files of assets/: a renamed file would silently lose its default."""
    for items in SOURCES.values():
        for relative in items.values():
            assert (ASSETS / relative).is_file(), relative


def test_defaults_follow_the_mode(client, checkpoint_store):
    assert client.get("/input/defaults").json()["external_data/fkt"]["filename"] == "external_data_fkt.csv"

    checkpoint_store.mode["test_mode"] = True

    assert client.get("/input/defaults").json() == {
        "config/Malaria": {"filename": "config.json", "size": 17},
        "external_data/fkt": {"filename": "external_data.csv", "size": 30},
    }


def test_preview_of_a_default(client):
    assert client.get("/input/defaults/config/Malaria/preview").json() == {"model": "prod"}
    csv = client.get("/input/defaults/external_data/fkt/preview").json()
    assert (csv["columns"], csv["total_rows"]) == (["orgUnit", "period", "x"], 1)
    assert client.get("/input/defaults/config/Cholera/preview").status_code == 404


def test_using_a_default_needs_an_open_run(client, tmp_path, checkpoint_store):
    _import(checkpoint_store)

    assert client.post("/input/files/config/from-default").status_code == 409
    assert not (tmp_path / "input" / "config.json").exists()


def test_using_a_default_writes_the_open_run_s_file_like_an_upload(client, tmp_path, checkpoint_store):
    checkpoint_store.set_cycle("202001")
    _import(checkpoint_store)
    checkpoint_store.open_run("COM/Malaria")

    assert client.post("/input/files/config/from-default").json() == {"saved": "input/config.json"}
    assert client.post("/input/files/external_data/from-default").status_code == 200

    assert json.loads((tmp_path / "input/config.json").read_text()) == {"model": "prod", "forecast_start": "202001"}
    assert (tmp_path / "input/external_data.csv").read_text() == "orgUnit,period,x\nOU1,202401,1\n"
    items = {i["item"]: i["status"] for i in checkpoint_store.progress()["steps"][1]["items"]}
    assert items["config/Malaria"] == items["external_data/fkt"] == "success"


def test_no_default_for_the_open_run_s_item_is_a_404(client, checkpoint_store):
    _import(checkpoint_store)
    checkpoint_store.open_run("CSB/Malaria")  # external_data/csb has no default in TEST_SOURCES

    assert client.post("/input/files/external_data/from-default").status_code == 404
