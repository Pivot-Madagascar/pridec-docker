from typing import Protocol


class EventSubscriber(Protocol):
    """One subscription to a job's live events (EventPublisher's), for one log WebSocket: a new one per connection."""

    async def subscribe(self, job_id: str) -> None: ...

    async def next_event(self, timeout: float) -> str | None:
        """The next event as published (JSON text), None when none came within `timeout` seconds."""
        ...

    async def close(self) -> None: ...
