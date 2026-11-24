"""GET /output/archive zips input/ and output/, without following symbolic links."""
import io
import zipfile
from types import SimpleNamespace

from etlhub.api.routers import forecast_report_router


def test_archive_holds_input_and_output_but_no_symlink(client, monkeypatch, tmp_path):
    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "config.json").write_text("{}")
    (tmp_path / "output" / "sub").mkdir(parents=True)
    (tmp_path / "output" / "sub" / "forecast.json").write_text("[]")
    (tmp_path / "secret.txt").write_text("outside")
    (tmp_path / "input" / "link.txt").symlink_to(tmp_path / "secret.txt")

    response = client.get("/output/archive")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert names == ["input/config.json", "output/sub/forecast.json"]


def test_archive_of_empty_folders_is_404(client, monkeypatch, tmp_path):
    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))

    assert client.get("/output/archive").status_code == 404


def test_archive_of_input_only_holds_the_files_the_forecast_reads(client, monkeypatch, tmp_path):
    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "disease_data.json").write_text("[]")
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "forecast.json").write_text("[]")

    response = client.get("/output/archive", params={"folder": "input"})

    assert response.status_code == 200
    assert 'filename="pridec_input.zip"' in response.headers["content-disposition"]
    assert zipfile.ZipFile(io.BytesIO(response.content)).namelist() == ["input/disease_data.json"]
    (tmp_path / "input" / "disease_data.json").unlink()
    assert client.get("/output/archive", params={"folder": "input"}).status_code == 404  # output/ never counts then
    assert client.get("/output/archive", params={"folder": "secret"}).status_code == 422


def test_archive_serves_the_folders_of_the_session_s_mode(app, monkeypatch, tmp_path):
    """Test mode: <data_dir>/test/input; production: <data_dir>/input. The mode is the session's, set by the async
    get_current_user, and must reach this sync route (run in a worker thread)."""
    from fastapi.testclient import TestClient
    from etlhub.api.auth import get_current_user
    from etlhub.core.job_context import pipeline_test_mode

    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    for folder, name in ((tmp_path / "input", "production.json"), (tmp_path / "test" / "input", "test.json")):
        folder.mkdir(parents=True)
        (folder / name).write_text("{}")

    def session_of(test_mode: bool):
        async def logged_in() -> dict:
            pipeline_test_mode.set(test_mode)
            return {"username": "tester"}
        return logged_in

    for test_mode, expected in ((True, ["input/test.json"]), (False, ["input/production.json"])):
        app.dependency_overrides[get_current_user] = session_of(test_mode)
        response = TestClient(app).get("/output/archive", params={"folder": "input"})
        assert zipfile.ZipFile(io.BytesIO(response.content)).namelist() == expected
