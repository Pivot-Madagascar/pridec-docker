from typing import Protocol


class WebhookNotifier(Protocol):
    """POSTs a job's end to the webhook_url given at its launch. Never raises: a failure is logged, never the URL
    (its path or query may carry a token)."""

    def post(self, url: str, job_id: str, body: dict) -> None: ...
