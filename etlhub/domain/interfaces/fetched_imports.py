from typing import Protocol


class FetchedImports(Protocol):
    """The last fetch of each Pivot import (pivot_dhis_tools' items: dataElement, fetched_data, summary), in the pass
    and mode served. A new fetch of an import replaces its items whole; an import never fetched there has none."""

    def save(self, task: str, items: list[dict]) -> None: ...

    def load(self, task: str) -> list[dict]: ...
