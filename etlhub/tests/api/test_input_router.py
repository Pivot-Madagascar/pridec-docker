import pytest
from fastapi.testclient import TestClient

CONFIG = b'{"pred_vars": ["rain"]}'
CSV = b"orgUnit,period,rain\nOU1,202401,3.2\n"


@pytest.fixture
def input_dir(app, tmp_path):
    from etlhub.core.dependencies import get_input_upload_service
    from etlhub.application.use_cases.input_upload_service import InputUploadService
    from tests.conftest import OpenGate

    # tmp_path itself also holds the request tracker db (autouse fixture).
    directory = tmp_path / "input"
    directory.mkdir()
    app.dependency_overrides[get_input_upload_service] = lambda: InputUploadService(directory, OpenGate())
    yield directory
    app.dependency_overrides.clear()


def _upload(app, name: str, content: bytes):
    return TestClient(app).post(f"/input/files/{name}", files={"file": ("anything", content)})


def _upload_both(app):
    _upload(app, "config", CONFIG)
    _upload(app, "external_data", CSV)


@pytest.mark.parametrize(
    "name, content, saved",
    [("config", CONFIG, "config.json"), ("external_data", CSV, "external_data.csv")],
)
def test_upload_writes_only_the_named_file(app, input_dir, name, content, saved):
    response = _upload(app, name, content)

    assert response.status_code == 200
    assert response.json() == {"saved": f"input/{saved}"}
    assert (input_dir / saved).read_bytes() == content
    assert [p.name for p in input_dir.iterdir()] == [saved]


def test_upload_replaces_the_existing_file(app, input_dir):
    (input_dir / "config.json").write_bytes(b'{"old": true}')

    _upload(app, "config", CONFIG)

    assert (input_dir / "config.json").read_bytes() == CONFIG


def test_upload_requires_a_file(app, input_dir):
    response = TestClient(app).post("/input/files/config")

    assert response.status_code == 422
    assert list(input_dir.iterdir()) == []


@pytest.mark.parametrize("name", ["other", "config.json"])
def test_upload_rejects_unknown_names(app, input_dir, name):
    assert _upload(app, name, CONFIG).status_code == 422
    assert list(input_dir.iterdir()) == []


@pytest.mark.parametrize("config", [b"{not json", b"[1, 2]", b"\xff\xfe"])
def test_upload_rejects_invalid_config_and_keeps_existing_file(app, input_dir, config):
    (input_dir / "config.json").write_bytes(b'{"old": true}')

    response = _upload(app, "config", config)

    assert response.status_code == 422
    assert "config.json" in response.json()["detail"]
    assert (input_dir / "config.json").read_bytes() == b'{"old": true}'


@pytest.mark.parametrize("csv", [b"orgUnit,rain\nOU1,3\n", b"", b"\xff\xfe"])
def test_upload_rejects_csv_without_required_columns(app, input_dir, csv):
    response = _upload(app, "external_data", csv)

    assert response.status_code == 422
    assert "external_data.csv" in response.json()["detail"]
    assert list(input_dir.iterdir()) == []


def test_upload_rejects_file_over_10_mb(app, input_dir):
    too_big = CSV + b"x" * (10 * 1024 * 1024)

    response = _upload(app, "external_data", too_big)

    assert response.status_code == 413
    assert list(input_dir.iterdir()) == []


def test_old_combined_upload_route_is_gone(app, input_dir):
    assert TestClient(app).post("/input/upload").status_code in (404, 405)


def test_files_status_when_input_is_empty(app, input_dir):
    response = TestClient(app).get("/input/files")

    assert response.status_code == 200
    assert response.json() == {"config": {"exists": False}, "external_data": {"exists": False}}


def test_files_status_after_upload(app, input_dir):
    _upload_both(app)

    body = TestClient(app).get("/input/files").json()

    assert body["config"]["exists"] is True
    assert body["config"]["size"] == len(CONFIG)
    assert body["external_data"]["size"] == len(CSV)
    assert "modified" in body["config"]


def test_delete_removes_only_the_named_file(app, input_dir):
    _upload_both(app)

    response = TestClient(app).delete("/input/files/config")

    assert response.status_code == 200
    assert response.json() == {"deleted": "input/config.json"}
    assert not (input_dir / "config.json").exists()
    assert (input_dir / "external_data.csv").read_bytes() == CSV


def test_delete_missing_file_returns_404(app, input_dir):
    response = TestClient(app).delete("/input/files/external_data")

    assert response.status_code == 404


@pytest.mark.parametrize("name", ["other", "..%2Fconfig.json", "config.json"])
def test_delete_rejects_unknown_names(app, input_dir, name):
    (input_dir / "config.json").write_bytes(CONFIG)

    response = TestClient(app).delete(f"/input/files/{name}")

    assert response.status_code in (404, 422)
    assert (input_dir / "config.json").read_bytes() == CONFIG


def _csv_rows(count: int) -> bytes:
    lines = ['"orgUnit","period","name",x']
    lines += [f'"OU{i % 3}","2024{(i % 12) + 1:02d}","Site, {i}",{i}.5' for i in range(count)]
    return ("\n".join(lines) + "\n").encode()


def test_config_preview_returns_the_json(app, input_dir):
    (input_dir / "config.json").write_bytes(CONFIG)

    response = TestClient(app).get("/input/files/config/preview")

    assert response.status_code == 200
    assert response.json() == {"pred_vars": ["rain"]}


def test_config_preview_404_when_absent(app, input_dir):
    assert TestClient(app).get("/input/files/config/preview").status_code == 404


def test_config_preview_422_when_json_is_broken(app, input_dir):
    (input_dir / "config.json").write_bytes(b"{broken")

    response = TestClient(app).get("/input/files/config/preview")

    assert response.status_code == 422
    assert "config.json" in response.json()["detail"]


def test_external_data_preview_limits_rows_and_summarises_the_whole_file(app, input_dir):
    (input_dir / "external_data.csv").write_bytes(_csv_rows(150))

    body = TestClient(app).get("/input/files/external_data/preview").json()

    assert body["columns"] == ["orgUnit", "period", "name", "x"]
    assert len(body["rows"]) == 100
    assert body["rows"][0] == ["OU0", "202401", "Site, 0", "0.5"]
    assert body["total_rows"] == 150
    assert body["period_range"] == ["202401", "202412"]
    assert body["org_units"] == 3


def test_external_data_preview_respects_limit(app, input_dir):
    (input_dir / "external_data.csv").write_bytes(_csv_rows(20))

    body = TestClient(app).get("/input/files/external_data/preview?limit=5").json()

    assert len(body["rows"]) == 5
    assert body["total_rows"] == 20


@pytest.mark.parametrize("limit", [0, 501])
def test_external_data_preview_rejects_out_of_range_limit(app, input_dir, limit):
    (input_dir / "external_data.csv").write_bytes(_csv_rows(1))

    assert TestClient(app).get(f"/input/files/external_data/preview?limit={limit}").status_code == 422


def test_external_data_preview_404_when_absent(app, input_dir):
    assert TestClient(app).get("/input/files/external_data/preview").status_code == 404
