"""DHIS2 calls of the login (DHIS2Accounts port): GET /api/me, create and revoke personal access tokens (PAT).

Login exchanges a DHIS2 username/password for a PAT. The PAT never leaves the server.
"""
import logging
import re
from contextlib import contextmanager

import httpx

from etlhub.core.config import get_settings
from etlhub.domain.exceptions import DHIS2Error

logger = logging.getLogger(__name__)

_UID = re.compile(r"^[A-Za-z0-9]{11}$")
# Attributes DHIS2 2.40 requires to create a PAT (checked manually against 2.40.3).
_PAT_ATTRIBUTES = [{"type": "MethodAllowedList", "allowedMethods": ["GET", "POST", "PUT", "PATCH", "DELETE"]}]


def _token_header(token: str) -> dict:
    return {"Authorization": f"ApiToken {token}"}


@contextmanager
def _unreachable():
    """httpx errors become the domain's DHIS2Error (same message)."""
    try:
        yield
    except httpx.HTTPError as e:
        raise DHIS2Error(str(e)) from e


class HttpDHIS2Accounts:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._transport = transport  # tests only (httpx.MockTransport)
        self.client: httpx.Client | None = None

    def __enter__(self) -> "HttpDHIS2Accounts":
        # No redirects: credentials must only ever go to the allowed host.
        self.client = httpx.Client(follow_redirects=False, timeout=get_settings().dhis2_auth_timeout,
                                   transport=self._transport)
        return self

    def __exit__(self, *exc_info) -> None:
        self.client.close()

    def fetch_me(self, url: str, *, auth: tuple | None = None, token: str | None = None) -> dict | None:
        """Return the DHIS2 user for these credentials, or None if DHIS2 rejects them."""
        with _unreachable():
            response = self.client.get(f"{url}/api/me.json", auth=auth, headers=_token_header(token) if token else None)
        if response.status_code in (401, 403):
            return None
        if response.status_code != 200:
            raise DHIS2Error(f"GET /api/me returned {response.status_code}")
        try:
            data = response.json()
        except ValueError as e:
            raise DHIS2Error("GET /api/me returned invalid JSON") from e
        return {k: data.get(k) for k in ("id", "email", "username", "displayName")}

    def create_pat(self, url: str, auth: tuple, expire_ms: int) -> tuple[str, str]:
        """Create a PAT for the Basic-auth user. Return (key, uid)."""
        with _unreachable():
            response = self.client.post(
                f"{url}/api/apiToken",
                json={"expire": expire_ms, "attributes": _PAT_ATTRIBUTES},
                auth=auth,
            )
        if response.status_code != 201:
            raise DHIS2Error(f"POST /api/apiToken returned {response.status_code}")
        try:
            body = response.json()["response"]
            key, uid = body["key"], body["uid"]
        except (ValueError, KeyError, TypeError) as e:
            raise DHIS2Error("POST /api/apiToken returned an unexpected body") from e
        if not key.startswith("d2pat_") or not _UID.match(uid):
            raise DHIS2Error("POST /api/apiToken returned an unexpected key or uid")
        return key, uid

    def revoke_pat(self, url: str, uid: str, *, auth: tuple | None = None, token: str | None = None) -> bool:
        """Delete a PAT in DHIS2. Never raises: a failed revocation is logged, the token expires anyway."""
        if not _UID.match(uid):
            logger.warning("Not revoking DHIS2 token: invalid uid")
            return False
        try:
            response = self.client.delete(
                f"{url}/api/apiToken/{uid}", auth=auth, headers=_token_header(token) if token else None
            )
        except httpx.HTTPError as e:
            logger.warning("Could not revoke DHIS2 token uid=%s: %s", uid, e)
            return False
        if response.status_code != 200:
            logger.warning("DHIS2 refused to revoke token uid=%s: status %s", uid, response.status_code)
            return False
        logger.info("Revoked DHIS2 token uid=%s", uid)
        return True
