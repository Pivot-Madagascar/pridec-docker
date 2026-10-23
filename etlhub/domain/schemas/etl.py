from pydantic import BaseModel, Field


class ETLResponse(BaseModel):
    status: str = Field(default="", examples=["accepted", "success", "error"])
    message: str = Field(default="", examples=["Task started in background", "Job completed successfully"])
    job_id: str = Field(default="", examples=["import_gee_a1b2c3d4", "forecast_x7y8z9w0"])
    webhook_url: str | None = Field(default=None, examples=["https://callback.example.com/webhook"])

