from etlhub.infrastructure.job_store import JobStore


def test_job_store_get_missing():
    store = JobStore()
    JobStore._jobs.clear()
    assert store.get("missing") is None


def test_job_store_set_and_get():
    store = JobStore()
    JobStore._jobs.clear()
    data = {"status": "running"}
    store.set("job1", data)
    assert store.get("job1") == data


def test_job_store_overwrites():
    store = JobStore()
    JobStore._jobs.clear()
    store.set("job1", {"status": "running"})
    store.set("job1", {"status": "success"})
    assert store.get("job1")["status"] == "success"


def test_load_from_file_missing(tmp_path):
    store = JobStore()
    result = store.load_from_file("nonexistent", str(tmp_path))
    assert result is None


def test_load_from_file_exists(tmp_path):
    store = JobStore()
    import json
    job_id = "job1"
    data = {"status": "success", "job_id": job_id}
    (tmp_path / f"{job_id}.json").write_text(json.dumps(data))
    result = store.load_from_file(job_id, str(tmp_path))
    assert result == data
