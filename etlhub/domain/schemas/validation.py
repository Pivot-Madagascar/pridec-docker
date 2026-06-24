from pydantic import BaseModel


class ValidationResponse(BaseModel):
    status: str = ""
    message: str = ""
    job_id: str = ""
    validation_messages: list[str] = []
    validation_errors: list[str] = []
    validated_config: str = ""
    validated_data: str = ""
    validated_polygons: str = ""
