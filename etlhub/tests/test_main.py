from fastapi.testclient import TestClient

from etlhub.main import app

client = TestClient(app)


def test_root_returns_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_root_contains_title():
    resp = client.get("/")
    assert "PRIDE-C ETL" in resp.text


def test_root_contains_links():
    resp = client.get("/")
    assert "/docs" in resp.text
