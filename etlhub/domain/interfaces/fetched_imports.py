from typing import Protocol


class FetchedImports(Protocol):
    """The last fetch of each Pivot import (pivot_dhis_tools' items: dataElement, fetched_data, summary), and since
    2026-11-24 import_gee's per-variable states (gee_import.py), in the pass and mode served. A new fetch or import
    replaces its items whole; an import never run there has none."""

    def save(self, task: str, items: list[dict]) -> None: ...

    def load(self, task: str) -> list[dict]: ...
