class ETLException(Exception):
    pass


# Not ETLExceptions: main.py's ETLException handler would answer them; the auth router maps them itself (502, 503).
class DHIS2Error(Exception):
    """DHIS2 is unreachable or answered something unexpected (DHIS2Accounts)."""


class AuthStoreUnavailable(Exception):
    """The session and credential store (Redis) failed (AuthStore)."""


class JobNotFoundError(ETLException):
    pass


class ValidationError(ETLException):
    pass


class PipelineBlockedError(ETLException):
    """Another job is running, or a previous checkpoint is not in success yet (409)."""


class ConfirmationRequiredError(PipelineBlockedError):
    """Relaunching an item already in success needs confirm=true (409 with the impact)."""

    def __init__(self, message: str, impact: dict):
        super().__init__(message)
        self.impact = impact