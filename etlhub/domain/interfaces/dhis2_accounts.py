from typing import Protocol, Self


class DHIS2Accounts(Protocol):
    """The DHIS2 calls of the login: who the credentials are, and the account's personal access tokens (PAT).

    Used as a context manager: one connection for the calls of a login or logout. fetch_me and create_pat raise
    DHIS2Error (domain.exceptions) when DHIS2 is unreachable or answers something unexpected."""

    def __enter__(self) -> Self: ...

    def __exit__(self, *exc_info) -> None: ...

    def fetch_me(self, url: str, *, auth: tuple | None = None, token: str | None = None) -> dict | None:
        """The DHIS2 user {id, email, username, displayName}, or None if DHIS2 rejects the credentials."""

    def create_pat(self, url: str, auth: tuple, expire_ms: int) -> tuple[str, str]:
        """Create a PAT for the Basic-auth user. Return (key, uid)."""

    def revoke_pat(self, url: str, uid: str, *, auth: tuple | None = None, token: str | None = None) -> bool:
        """Delete a PAT. Never raises: False when it failed (the token expires anyway)."""
