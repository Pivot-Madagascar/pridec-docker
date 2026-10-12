class ETLException(Exception):
    pass


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