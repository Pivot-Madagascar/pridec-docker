from pydantic import BaseModel


class ETLResponse(BaseModel):
    status: str = ""
    message: str = ""
    job_id: str = ""
    webhook_url: str | None = None


class WebhookNotification(BaseModel):
    job_id: str
    status: str
    message: str
    logs_url: str | None = None
