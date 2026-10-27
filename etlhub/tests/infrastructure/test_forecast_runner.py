import contextlib
from types import SimpleNamespace

import pytest

from etlhub.infrastructure import forecast_runner

PARAMS = {"config_valid_path": "input/c.json", "input_valid_path": "input/i.json", "polygon_valid_path": "input/p.geojson"}


def _fake_popen(output, returncode, on_start=lambda cmd, kwargs: None):
    """Stands in for `docker run`: yields `output` line by line, then exits with `returncode`."""
    def popen(cmd, **kwargs):
        on_start(cmd, kwargs)
        return contextlib.nullcontext(SimpleNamespace(stdout=iter(output.splitlines(keepends=True)), returncode=returncode))
    return popen


@pytest.fixture
def runner_env(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("OTHER=1\n")
    settings = SimpleNamespace(host_pwd=str(tmp_path), data_dir=str(tmp_path), logs_dir=str(tmp_path / "logs"))
    monkeypatch.setattr(forecast_runner, "get_settings", lambda: settings)
    monkeypatch.setattr(forecast_runner.ConfigStore, "get_all", lambda self: {})
    return tmp_path


def test_missing_env_file_marks_job_as_error_without_running_docker(runner_env, monkeypatch, job_store):
    (runner_env / ".env").unlink()

    def no_docker(*args, **kwargs):
        raise AssertionError("docker must not run")

    monkeypatch.setattr(forecast_runner.subprocess, "Popen", no_docker)

    status = forecast_runner.run_rscript("forecast_noenv", {}, job_store)

    assert status["status"] == "error"
    assert ".env" in status["message"] and str(runner_env) in status["message"]
    assert job_store.records["forecast_noenv"]["status"] == "error"


def test_forecast_container_runs_as_the_worker_user_and_output_exists_first(runner_env, monkeypatch, job_store):
    monkeypatch.setattr(forecast_runner.os, "getuid", lambda: 1000)
    monkeypatch.setattr(forecast_runner.os, "getgid", lambda: 1000)
    seen = {}

    def on_start(cmd, kwargs):
        seen["cmd"] = cmd
        seen["output_existed"] = (runner_env / "output").is_dir()

    monkeypatch.setattr(forecast_runner.subprocess, "Popen", _fake_popen("stop here", 1, on_start))

    forecast_runner.run_rscript("forecast_user", PARAMS, job_store)

    cmd = seen["cmd"]
    assert cmd[cmd.index("--user") + 1] == "1000:1000"
    assert "HOME=/tmp" in cmd
    assert seen["output_existed"]


def test_forecast_logs_keep_stderr_merged_with_stdout(runner_env, monkeypatch, job_store):
    seen = {}
    monkeypatch.setattr(forecast_runner.subprocess, "Popen", _fake_popen(
        "$pred_vars\n✔ SUCCESS: Forecast created.", 0, lambda cmd, kwargs: seen.update(kwargs)))

    status = forecast_runner.run_rscript("forecast_logs", PARAMS, job_store)

    assert seen["stderr"] is forecast_runner.subprocess.STDOUT
    assert status["status"] == "success" and "SUCCESS: Forecast created" in status["logs"]
    assert (runner_env / "logs" / "forecast_logs.json").exists()


def test_forecast_lines_are_stored_and_published_as_the_container_prints_them(runner_env, monkeypatch, job_store):
    events = []

    monkeypatch.setattr(job_store, "append_logs", lambda job_id, text: events.append(("stored", text)))
    from etlhub.infrastructure import etl_events
    monkeypatch.setattr(etl_events, "publish_log", lambda job_id, level, message: events.append(("published", message)))
    monkeypatch.setattr(forecast_runner.subprocess, "Popen", _fake_popen("one\ntwo\nthree\n", 0))

    status = forecast_runner.run_rscript("forecast_live", PARAMS, job_store)

    # One line at a time, stored before it is published, and no final blob repeating them.
    assert events == [("stored", "one\n"), ("published", "one"), ("stored", "two\n"), ("published", "two"),
                      ("stored", "three\n"), ("published", "three")]
    assert status["status"] == "success" and status["logs"] == "one\ntwo\nthree\n"
