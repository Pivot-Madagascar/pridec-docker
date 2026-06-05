from fastapi import FastAPI
from fastapi.testclient import TestClient

from etlhub.api.middleware import setup_cors


def test_cors_setup_adds_middleware():
    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"ok": True}

    setup_cors(app)
    client = TestClient(app)

    resp = client.get("/", headers={"Origin": "http://example.com"})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "*"
    assert resp.headers["access-control-allow-credentials"] == "true"
