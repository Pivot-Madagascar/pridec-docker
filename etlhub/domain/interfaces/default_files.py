from pathlib import Path
from typing import Protocol


class DefaultFileSource(Protocol):
    """Default config.json / external_data.csv per item (config/<disease>, external_data/<level>) and mode."""

    def current(self, mode: str) -> dict[str, dict]: ...

    def path(self, mode: str, item: str) -> Path | None: ...
