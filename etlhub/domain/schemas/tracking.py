
from pydantic import BaseModel, Field


class ServiceCallLog(BaseModel):
    service: str = Field(examples=["gee", "pivot_com"])
    method: str = Field(examples=["GET", "POST"])
    url: str = Field(examples=["https://api.example.com/data"])
    status_code: int | None = Field(default=None, examples=[200, 404, 500])
    duration_ms: float | None = Field(default=None, examples=[150.5, 230.0])
    error: str | None = Field(default=None, examples=["Connection timeout"])


class RequestLog(BaseModel):
    request_id: str = Field(examples=["a1b2c3d4-e5f6-7890"])
    method: str = Field(examples=["GET", "POST", "PUT"])
    url: str = Field(examples=["/api/tracking/requests"])
    status_code: int = Field(examples=[200, 202, 404])
    duration_ms: float = Field(examples=[45.2, 120.5])
    client_host: str | None = Field(default=None, examples=["127.0.0.1", "192.168.1.1"])
    services: list[ServiceCallLog] = []
    error: str | None = Field(default=None, examples=["Invalid parameters"])


class ETLLog(BaseModel):
    job_id: str = Field(examples=["import_gee_a1b2c3d4"])
    status: str | None = Field(default=None, examples=["running", "success", "error"])
    message: str | None = Field(default=None, examples=["Import in progress"])
    logs: str | None = Field(default=None, examples=["Step 1: fetched data\nStep 2: processing..."])
