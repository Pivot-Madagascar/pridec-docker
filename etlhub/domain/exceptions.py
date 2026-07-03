class ETLException(Exception):
    pass


class JobNotFoundError(ETLException):
    pass


class ValidationError(ETLException):
    pass


class TaskLaunchError(ETLException):
    pass