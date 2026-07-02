from typing import Protocol, runtime_checkable

@runtime_checkable
class WebhookNotifier(Protocol):
    def send(self, webhook_url: str, job_id: str, status: str, message: str, logs_url: str | None = None) -> None: ...