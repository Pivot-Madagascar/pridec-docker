"""Log WebSocket: history, live entries, end of job, unknown job."""
import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from etlhub.api.websockets import etl_logs

JOB = "import_gee_1234abcd"


def _job(fake, status, message=None):
    fake.data[f"job:{JOB}"] = json.dumps({"job_id": JOB, "status": status, "message": message, "started": "t0"})


def _connect(app):
    return TestClient(app).websocket_connect(f"/api/tracking/etl-logs/{JOB}")


def test_unknown_job_is_closed_with_4004(app, fake_ws_redis):
    with _connect(app) as ws:
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 4004


def test_pending_job_without_logs_stays_open_and_streams_until_the_end(app, fake_ws_redis):
    _job(fake_ws_redis, "pending", "Queued")

    with _connect(app) as ws:
        assert ws.receive_json() == {"type": "etl_log_history", "job_id": JOB, "logs": ""}
        assert ws.receive_json()["status"] == "pending"

        fake_ws_redis.queue.append(json.dumps({"type": "etl_log_entry", "job_id": JOB, "message": "step 1"}))
        assert ws.receive_json()["message"] == "step 1"

        fake_ws_redis.queue.append(json.dumps({"type": "job_status_update", "job_id": JOB, "status": "success"}))
        assert ws.receive_json()["status"] == "success"
        assert ws.receive_json() == {"type": "etl_log_complete", "job_id": JOB, "final_status": "success"}
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 1000


def test_final_event_already_published_ends_the_stream_and_cleans_up(app, fake_ws_redis):
    _job(fake_ws_redis, "running")
    fake_ws_redis.queue.append(json.dumps({"type": "job_status_update", "job_id": JOB, "status": "error"}))

    with _connect(app) as ws:
        messages = [ws.receive_json() for _ in range(4)]

    assert fake_ws_redis.pubsubs[0].channels == [] and fake_ws_redis.pubsubs[0].closed
    assert messages[-1] == {"type": "etl_log_complete", "job_id": JOB, "final_status": "error"}


def test_a_missed_final_event_is_caught_by_the_status_check(app, fake_ws_redis, monkeypatch):
    monkeypatch.setattr(etl_logs, "STATUS_CHECK_SECONDS", 0.05)
    _job(fake_ws_redis, "running")

    with _connect(app) as ws:
        ws.receive_json()  # history
        ws.receive_json()  # running
        _job(fake_ws_redis, "success", "done")  # finished, but the event never reached us
        assert ws.receive_json()["status"] == "success"
        assert ws.receive_json()["final_status"] == "success"


def test_finished_job_sends_history_and_completes(app, fake_ws_redis):
    _job(fake_ws_redis, "success", "done")
    fake_ws_redis.data[f"etl_logs:{JOB}"] = "line 1\nline 2"

    with _connect(app) as ws:
        assert ws.receive_json()["logs"] == "line 1\nline 2"
        assert ws.receive_json()["status"] == "success"
        assert ws.receive_json()["final_status"] == "success"


def test_logs_without_job_record_complete_without_status(app, fake_ws_redis, tmp_path):
    (tmp_path / f"{JOB}.log").write_text("old run")

    with _connect(app) as ws:
        assert ws.receive_json()["logs"] == "old run"
        assert ws.receive_json() == {"type": "etl_log_complete", "job_id": JOB, "final_status": None}
