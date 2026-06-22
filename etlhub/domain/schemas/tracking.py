
from pydantic import BaseModel


class ServiceCallLog(BaseModel):
    service: str
    method: str
    url: str
    status_code: int | None = None
    duration_ms: float | None = None
    error: str | None = None


class RequestLog(BaseModel):
    request_id: str
    method: str
    url: str
    status_code: int
    duration_ms: float
    client_host: str | None = None
    services: list[ServiceCallLog] = []
    error: str | None = None


class ETLLog(BaseModel):
    job_id: str
    status: str | None = None
    message: str | None = None
    logs: str | None = None
