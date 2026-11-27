from typing import Protocol


class ImportSettings(Protocol):
    """What the import availability check and the import parameters read of the configuration (under etlhub: the
    session's login and the pass, etlhub/script_config.py)."""

    def read(self) -> dict:
        """{"dhis_url", "dhis_token", "parent_ou", "gee_variables"}. Raises EnvironmentError when DHIS_URL, DHIS_TOKEN
        or PARENT_OU is missing."""
