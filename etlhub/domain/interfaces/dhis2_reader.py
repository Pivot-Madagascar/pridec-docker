from typing import Protocol


class DHIS2Reader(Protocol):
    """The DHIS2 reads of the import availability check (check_import_availability.py), with the caller's URL and
    token. Read only. Each raises on an HTTP or DHIS2 error: the check marks the row it was reading."""

    def data_values(self, url: str, token: str, params: dict) -> list[dict]:
        """The stored values of /api/dataValueSets for these params (orgUnit, period, lastUpdated, ...)."""

    def analytics(self, url: str, token: str, code: str, periods: list[str], ou_query: str) -> list[dict]:
        """The analytics rows (dx, ou, pe, value) of one dataElement code over these periods and org units."""

    def system_info(self, url: str, token: str) -> dict:
        """/api/system/info."""
