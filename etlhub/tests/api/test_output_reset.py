"""DELETE /output/reset deletes output/ in Python only: no subprocess, no sudo."""
import os
import shutil
from types import SimpleNamespace

from etlhub.api.routers import forecast_report_router


def _settings(monkeypatch, tmp_path):
    settings = SimpleNamespace(data_dir=str(tmp_path))
    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: settings)
    (tmp_path / ".output_sig").write_text("sig")
    (tmp_path / "output" / "sub").mkdir(parents=True)
    (tmp_path / "output" / "forecast.json").write_text("{}")
    (tmp_path / "output" / "sub" / "x.html").write_text("<p>")


def test_reset_deletes_output_and_signature(client, monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)

    response = client.delete("/output/reset")

    assert response.status_code == 200
    assert not (tmp_path / "output").exists()
    assert not (tmp_path / ".output_sig").exists()


def test_reset_never_falls_back_to_sudo(client, monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)

    def denied(path):
        raise PermissionError("owned by root")

    monkeypatch.setattr(forecast_report_router.shutil, "rmtree", denied)
    assert not hasattr(forecast_report_router, "subprocess")

    response = client.delete("/output/reset")

    assert response.status_code == 500
    assert "another user" in response.json()["detail"]
    assert (tmp_path / ".output_sig").exists()  # nothing half-cleaned


def test_reset_without_signature_is_refused(client, monkeypatch, tmp_path):
    settings = SimpleNamespace(data_dir=str(tmp_path))
    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: settings)

    assert client.delete("/output/reset").status_code == 403
