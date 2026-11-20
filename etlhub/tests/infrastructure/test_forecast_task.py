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
    monkeypatch.setattr(tasks.task_etl, "apply_async",
                        lambda args, kwargs, task_id: queued.append((job_store.get("import_gee_1234abcd"), task_id)))

    tasks.CeleryTaskLauncher().launch("import_gee", "import_gee_1234abcd")

    record, task_id = queued[0]
    assert record["status"] == "pending"
    assert task_id == "import_gee_1234abcd"  # is_active finds the job among the workers' tasks by this id


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


def test_a_validate_inputs_failure_keeps_its_reason_in_the_job_message(job_store):
    """etl.scripts.validate_inputs.ValidationError has no message: str(e) is empty, its errors carry the reason."""
    from etl.scripts.validate_inputs import ValidationError
    from etlhub.application.use_cases import etl_use_cases
    from etlhub.domain.exceptions import ETLException
    from etlhub.infrastructure import etl_events

    def job():
        raise ValidationError(errors=["ERROR: missing predictor variables:mosquito_net"], messages=[])

    with pytest.raises(ETLException, match="validate_inputs failed: ERROR: missing predictor variables:mosquito_net"):
        etl_use_cases._execute_etl_job(job, etl_use_cases._JobLogger(job_store, "validate_inputs_1", etl_events),
                                       "validate_inputs")


@pytest.mark.parametrize("replies, expected", [
    ({"w1@host": {"import_gee_1": ["active", {}]}}, True),
    ({"w1@host": {}, "w2@host": {"import_gee_1": ["reserved", {}]}}, True),  # prefetched by a restarted worker
    ({"w1@host": {"import_gee_1": ["ready", {}]}}, False),  # finished
    ({"w1@host": {}}, False),  # the workers answered: none runs it
    (None, None),  # no worker answered: unknown
])
def test_is_active_asks_the_workers_by_job_id(monkeypatch, replies, expected):
    asked = []

    class Inspect:
        def query_task(self, *ids):
            asked.extend(ids)
            return replies

    monkeypatch.setattr(tasks.celery_app.control, "inspect", lambda: Inspect())

    assert tasks.CeleryTaskLauncher().is_active("import_gee_1") is expected
    assert asked == ["import_gee_1"]


def test_is_active_is_true_for_an_inline_job_of_this_process_and_unknown_when_the_broker_is_down(monkeypatch):
    def broker_down():
        raise ConnectionError("broker down")

    monkeypatch.setattr(tasks.celery_app.control, "inspect", broker_down)
    monkeypatch.setattr(tasks, "RUNNING_INLINE", {"post_forecast_1"})

    assert tasks.CeleryTaskLauncher().is_active("post_forecast_1") is True
    assert tasks.CeleryTaskLauncher().is_active("import_gee_1") is None


@pytest.mark.parametrize("chosen", [True, False])
def test_the_scripts_read_the_dryrun_of_their_launch_during_the_job_only(job_store, chosen):
    from etl.scripts.config import get_dry_run
    from etlhub.application.use_cases import etl_use_cases
    from etlhub.core.job_context import job_dry_run
    from etlhub.infrastructure import etl_events
    seen = []

    etl_use_cases._execute_etl_job(lambda: seen.append(get_dry_run()),
                                   etl_use_cases._JobLogger(job_store, "import_gee_1", etl_events), "import_gee",
                                   dry_run=chosen)

    assert seen == [chosen]
    assert job_dry_run.get() is None  # after the job: DRYRUN of Redis (.env) again


def test_a_job_is_queued_with_the_users_mode_and_served_in_it(monkeypatch, job_store, webhooks):
    from etlhub.core.job_context import current_test_mode, pipeline_test_mode
    queued, seen = [], []
    monkeypatch.setattr(tasks.task_etl, "apply_async", lambda args, kwargs, task_id: queued.append(kwargs))
    pipeline_test_mode.set(True)  # a test-mode session launches

    tasks.CeleryTaskLauncher().launch("import_gee", "import_gee_1234abcd")
    assert queued[0]["test_mode"] is True

    monkeypatch.setattr(tasks, "run_etl_job", lambda *a, **kw: seen.append(current_test_mode()))
    pipeline_test_mode.set(False)  # the worker's own context: production by default in the tests
    tasks.task_etl.run("import_gee", "import_gee_1234abcd", test_mode=True)
    assert seen == [True]
    assert current_test_mode() is False  # reset after the job
