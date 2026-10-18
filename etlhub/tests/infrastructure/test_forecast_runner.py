from types import SimpleNamespace

from etlhub.infrastructure import forecast_runner


class _RecordingJobStore:
    def __init__(self):
        self.records = {}

    def set(self, job_id, data):
        self.records[job_id] = dict(data)

    def save_logs(self, job_id, logs):
        pass


def test_missing_env_file_marks_job_as_error_without_running_docker(tmp_path, monkeypatch):
    settings = SimpleNamespace(host_pwd=str(tmp_path), data_dir=str(tmp_path), logs_dir=str(tmp_path / "logs"))
    monkeypatch.setattr(forecast_runner, "get_settings", lambda: settings)
    monkeypatch.setattr(forecast_runner, "_get_output_dir", lambda: str(tmp_path / "output"))
    monkeypatch.setattr(forecast_runner, "generate_signature", lambda: "sig")

    def no_docker(*args, **kwargs):
        raise AssertionError("docker must not run")

    monkeypatch.setattr(forecast_runner.subprocess, "run", no_docker)
    job_store = _RecordingJobStore()

    status = forecast_runner.run_rscript("forecast_noenv", {}, job_store)

    assert status["status"] == "error"
    assert ".env" in status["message"] and str(tmp_path) in status["message"]
    assert job_store.records["forecast_noenv"]["status"] == "error"


def test_forecast_container_runs_as_the_worker_user_and_output_exists_first(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("OTHER=1\n")
    settings = SimpleNamespace(host_pwd=str(tmp_path), data_dir=str(tmp_path), logs_dir=str(tmp_path / "logs"))
    monkeypatch.setattr(forecast_runner, "get_settings", lambda: settings)
    monkeypatch.setattr(forecast_runner, "_get_output_dir", lambda: str(tmp_path / "output"))
    monkeypatch.setattr(forecast_runner, "generate_signature", lambda: "sig")
    monkeypatch.setattr(forecast_runner.ConfigStore, "get_all", lambda self: {})
    monkeypatch.setattr(forecast_runner.os, "getuid", lambda: 1000)
    monkeypatch.setattr(forecast_runner.os, "getgid", lambda: 1000)
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["output_existed"] = (tmp_path / "output").is_dir()
        return SimpleNamespace(returncode=1, stdout="stop here")

    monkeypatch.setattr(forecast_runner.subprocess, "run", fake_run)

    forecast_runner.run_rscript("forecast_user", {
        "config_valid_path": "input/c.json", "input_valid_path": "input/i.json", "polygon_valid_path": "input/p.geojson",
    }, _RecordingJobStore())

    cmd = seen["cmd"]
    assert cmd[cmd.index("--user") + 1] == "1000:1000"
    assert "HOME=/tmp" in cmd
    assert seen["output_existed"]


def test_forecast_logs_keep_stderr_merged_with_stdout(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("OTHER=1\n")
    settings = SimpleNamespace(host_pwd=str(tmp_path), data_dir=str(tmp_path), logs_dir=str(tmp_path / "logs"))
    monkeypatch.setattr(forecast_runner, "get_settings", lambda: settings)
    monkeypatch.setattr(forecast_runner, "_get_output_dir", lambda: str(tmp_path / "output"))
    monkeypatch.setattr(forecast_runner, "generate_signature", lambda: "sig")
    monkeypatch.setattr(forecast_runner.ConfigStore, "get_all", lambda self: {})
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="$pred_vars\n\u2714 SUCCESS: Forecast created.")

    monkeypatch.setattr(forecast_runner.subprocess, "run", fake_run)

    status = forecast_runner.run_rscript("forecast_logs", {
        "config_valid_path": "input/c.json", "input_valid_path": "input/i.json", "polygon_valid_path": "input/p.geojson",
    }, _RecordingJobStore())

    assert seen["stderr"] is forecast_runner.subprocess.STDOUT
    assert status["status"] == "success" and "SUCCESS: Forecast created" in status["logs"]
    assert (tmp_path / "logs" / "forecast_logs.json").exists()
