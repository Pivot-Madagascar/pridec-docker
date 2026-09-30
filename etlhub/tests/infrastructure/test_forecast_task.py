import pytest

from etlhub.infrastructure import tasks


class InMemoryJobStore:
    records: dict = {}

    def get(self, job_id):
        record = self.records.get(job_id)
        return dict(record) if record else None

    def set(self, job_id, data):
        self.records[job_id] = dict(data)

    def save_logs(self, job_id, logs):
        pass


@pytest.fixture
def job_store(monkeypatch):
    InMemoryJobStore.records = {}
    monkeypatch.setattr(tasks, "JobStore", InMemoryJobStore)
    return InMemoryJobStore()


@pytest.fixture
def webhooks(monkeypatch):
    sent = []
    monkeypatch.setattr(tasks, "_send_webhook", lambda url, **kwargs: sent.append(kwargs))
    return sent


def _fake_rscript(final_status):
    def run(job_id, params, job_store):
        status = {
            "status": final_status,
            "started": "2026-09-30T10:00:00",
            "completed": "2026-09-30T10:05:00",
            "job_id": job_id,
            "logs": "R output",
        }
        if final_status == "error":
            status["message"] = "container exited with code 1"
        job_store.set(job_id, status)
        return status
    return run


def test_forecast_container_failure_marks_job_as_error(monkeypatch, job_store, webhooks):
    monkeypatch.setattr(tasks, "run_rscript", _fake_rscript("error"))

    with pytest.raises(tasks.ETLException):
        tasks.task_forecast.run("forecast_fail", {}, webhook_url="http://hook")

    record = job_store.get("forecast_fail")
    assert record["status"] == "error"
    assert record["message"] == "container exited with code 1"
    assert record["logs"] == "R output"
    assert webhooks[-1]["status"] == "error"


def test_forecast_success_keeps_container_details(monkeypatch, job_store, webhooks):
    monkeypatch.setattr(tasks, "run_rscript", _fake_rscript("success"))

    tasks.task_forecast.run("forecast_ok", {}, webhook_url="http://hook")

    record = job_store.get("forecast_ok")
    assert record["status"] == "success"
    assert record["started"] == "2026-09-30T10:00:00"
    assert record["completed"] == "2026-09-30T10:05:00"
    assert record["logs"] == "R output"
    assert webhooks[-1]["status"] == "success"
