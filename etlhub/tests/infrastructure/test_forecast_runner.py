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
