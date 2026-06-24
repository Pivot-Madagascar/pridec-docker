from pydantic import BaseModel, Field


class ForecastParams(BaseModel):
    config_valid_path: str = Field(default="input/config_valid.json")
    input_valid_path: str = Field(default="input/input_valid.json")
    polygon_valid_path: str = Field(default="input/polygon_valid.geojson")


class JobStatus(BaseModel):
    status: str
    job_id: str
    started: str | None = None
    completed: str | None = None
    logs: str | None = None
    message: str | None = None
