from pydantic import BaseModel


class ETLResponse(BaseModel):
    status: str = ""
    message: str = ""
    job_id: str = ""
