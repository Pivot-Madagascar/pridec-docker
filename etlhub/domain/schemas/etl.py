from pydantic import BaseModel, Field


class ETLResponse(BaseModel):
    status: str = Field(default="", examples=["accepted", "success", "error"])
    message: str = Field(default="", examples=["Task started in background", "Job completed successfully"])
    job_id: str = Field(default="", examples=["import_gee_a1b2c3d4", "forecast_x7y8z9w0"])
    webhook_url: str | None = Field(default=None, examples=["https://callback.example.com/webhook"])


class WebhookNotification(BaseModel):
    job_id: str = Field(examples=["import_gee_a1b2c3d4"])
    status: str = Field(examples=["success", "error", "running"])
    message: str = Field(examples=["Task completed"])
    logs_url: str | None = Field(default=None, examples=["/api/tracking/etl-logs/abc123"])
