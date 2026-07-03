from pydantic import BaseModel, Field


class ForecastParams(BaseModel):
    config_valid_path: str = Field(
        default="input/config_valid.json",
        examples=["input/config_valid.json", "data/config.json"]
    )
    input_valid_path: str = Field(
        default="input/input_valid.json",
        examples=["input/input_valid.json", "data/input.json"]
    )
    polygon_valid_path: str = Field(
        default="input/polygon_valid.geojson",
        examples=["input/polygon_valid.geojson", "data/boundaries.geojson"]
    )


class JobStatus(BaseModel):
    status: str = Field(examples=["running", "success", "error"])
    job_id: str = Field(examples=["forecast_a1b2c3d4"])
    started: str | None = Field(default=None, examples=["2024-01-15T10:30:00"])
    completed: str | None = Field(default=None, examples=["2024-01-15T10:35:00"])
    logs: str | None = Field(default=None, examples=["Processing step 1... OK"])
    message: str | None = Field(default=None, examples=["Pipeline completed"])
