from typing import Protocol


class EventPublisher(Protocol):
    """Live job events for the log WebSocket. Best effort: callers ignore its failures."""

    def publish_log(self, job_id: str, level: str, message: str) -> None: ...

    def publish_status(self, job_id: str, status: str, message: str | None = None) -> None: ...
