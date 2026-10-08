
from pydantic import BaseModel, Field


class RequestLog(BaseModel):
    request_id: str = Field(examples=["a1b2c3d4-e5f6-7890"])
    # UTC, ISO 8601. Missing on entries recorded before 2026-10-08.
    timestamp: str | None = Field(default=None, examples=["2026-10-08T12:30:00+00:00"])
    method: str = Field(examples=["GET", "POST", "PUT"])
    url: str = Field(examples=["/api/tracking/requests"])
    status_code: int = Field(examples=[200, 202, 404])
    duration_ms: float = Field(examples=[45.2, 120.5])
    client_host: str | None = Field(default=None, examples=["127.0.0.1", "192.168.1.1"])
    job_id: str | None = Field(default=None, examples=["import_gee_a1b2c3d4"], description="Job started or read by this request, if its JSON response had one")
    error: str | None = Field(default=None, examples=["RuntimeError: boom"], description="Set when the request raised an unhandled exception (status 500)")


class ETLLog(BaseModel):
    job_id: str = Field(examples=["import_gee_a1b2c3d4"])
    status: str | None = Field(default=None, examples=["running", "success", "error"])
    message: str | None = Field(default=None, examples=["Import in progress"])
    logs: str | None = Field(default=None, examples=["Step 1: fetched data\nStep 2: processing..."])
