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
