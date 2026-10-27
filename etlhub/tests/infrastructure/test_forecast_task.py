import pytest

from etlhub.infrastructure import tasks


@pytest.fixture
def job_store(job_store, monkeypatch):
    """conftest's job_store, also the one the tasks build with JobStore()."""
    monkeypatch.setattr(tasks, "JobStore", lambda: job_store)
    return job_store


@pytest.fixture
def webhooks(monkeypatch):
    sent = []
    monkeypatch.setattr(tasks, "notify_webhook", lambda url, job_id, status, message: sent.append({"status": status}))
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


def test_launch_records_the_job_as_pending_before_queueing(monkeypatch, job_store):
    queued = []
    monkeypatch.setattr(tasks.task_etl, "delay", lambda *a, **k: queued.append(job_store.get("import_gee_1234abcd")))

    tasks.CeleryTaskLauncher().launch("import_gee", "import_gee_1234abcd")

    assert queued[0]["status"] == "pending"


def test_generic_task_runs_the_job_with_its_kwargs(monkeypatch, job_store, webhooks):
    calls = []
    monkeypatch.setattr(tasks, "run_etl_job", lambda task_type, store, job_id, events, **kw: calls.append((task_type, job_id, events, kw)))

    tasks.task_etl.run("validate_inputs", "validate_inputs_1", webhook_url="http://hook", input_dir="input/x")

    assert calls == [("validate_inputs", "validate_inputs_1", tasks.etl_events, {"input_dir": "input/x"})]
    assert job_store.get("validate_inputs_1")["message"] == "validate inputs completed"
    assert webhooks[-1]["status"] == "success"


def test_a_gate_error_at_the_end_does_not_turn_a_success_into_an_error(monkeypatch, job_store, webhooks):
    # In test mode the gate lives in Redis: a Redis error must not mark a successful job as failed.
    class BrokenGate:
        def finish(self, job_id, status):
            raise ConnectionError("redis is down")
    monkeypatch.setattr(tasks, "get_checkpoint_store", BrokenGate)
    monkeypatch.setattr(tasks, "run_rscript", _fake_rscript("success"))

    tasks.task_forecast.run("forecast_ok", {})

    assert job_store.get("forecast_ok")["status"] == "success"
    assert [w["status"] for w in webhooks] == ["success"]


def test_etl_job_output_goes_to_the_job_logs_once_as_it_is_printed(job_store, monkeypatch):
    from etlhub.infrastructure import etl_events
    from etlhub.application.use_cases import etl_use_cases
    published = []
    monkeypatch.setattr(etl_events, "publish_log", lambda job_id, level, message: published.append(message))

    def job():
        print("step 1")
        assert job_store.get_logs("import_gee_1") == "step 1\n"  # stored before the job ends

    etl_use_cases._execute_etl_job(job, etl_use_cases._JobLogger(job_store, "import_gee_1", etl_events), "import_gee")

    assert job_store.get_logs("import_gee_1") == "step 1\n"
    assert "step 1" in published
