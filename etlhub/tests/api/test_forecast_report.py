"""GET /output/forecast_report.html: the report of the session's mode, 404 before the forecast, 500 if unreadable."""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from etlhub.api.routers import forecast_report_router


def test_report_of_the_session_s_mode(app, monkeypatch, tmp_path):
    """Production: <data_dir>/output; test mode: <data_dir>/test/output. Holds whether the handler is async or not:
    the mode set by the async get_current_user must reach it either way."""
    from etlhub.api.auth import get_current_user
    from etlhub.core.job_context import pipeline_test_mode

    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    for folder, html in ((tmp_path / "output", "<p>production</p>"), (tmp_path / "test" / "output", "<p>test</p>")):
        folder.mkdir(parents=True)
        (folder / "forecast_report.html").write_text(html, encoding="utf-8")

    def session_of(test_mode: bool):
        async def logged_in() -> dict:
            pipeline_test_mode.set(test_mode)
            return {"username": "tester"}
        return logged_in

    for test_mode, expected in ((True, "<p>test</p>"), (False, "<p>production</p>")):
        app.dependency_overrides[get_current_user] = session_of(test_mode)
        response = TestClient(app).get("/output/forecast_report.html")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert response.text == expected


def test_report_missing_is_404_and_unreadable_is_500(client, monkeypatch, tmp_path):
    monkeypatch.setattr(forecast_report_router, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))

    assert client.get("/output/forecast_report.html").status_code == 404

    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "forecast_report.html").write_bytes(b"\xff\xfe not utf-8")
    response = client.get("/output/forecast_report.html")
    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to read forecast report"}
