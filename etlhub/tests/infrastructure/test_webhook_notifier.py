"""The worker POSTs a job's end through the WebhookNotifier adapter (httpx replaced: no network)."""
from etlhub.infrastructure import tasks, webhook_notifier


def test_a_job_end_reaches_the_webhook_through_the_adapter(monkeypatch, job_store):
    monkeypatch.setattr(tasks, "JobStore", lambda: job_store)
    monkeypatch.setattr(tasks, "run_etl_job", lambda *args, **kw: None)
    sent = []
    monkeypatch.setattr(webhook_notifier.httpx, "post", lambda url, **kw: sent.append((url, kw)))

    tasks.task_etl.run("validate_inputs", "validate_inputs_1", webhook_url="https://hooks.example.org/x?token=t")

    assert sent == [("https://hooks.example.org/x?token=t", {
        "json": {"job_id": "validate_inputs_1", "status": "success", "message": "validate inputs completed",
                 "logs_url": "/api/tracking/etl-logs/validate_inputs_1"},
        "timeout": 10})]  # no follow_redirects: httpx's default, redirects are not followed
