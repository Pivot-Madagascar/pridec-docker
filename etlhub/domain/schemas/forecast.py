from pathlib import PurePosixPath

from pydantic import BaseModel, Field, field_validator


class ForecastParams(BaseModel):
    config_valid_path: str = Field(
        default="input/config_valid.json",
        examples=["input/config_valid.json", "input/run1/config_valid.json"]
    )
    input_valid_path: str = Field(
        default="input/input_valid.json",
        examples=["input/input_valid.json", "input/run1/input_valid.json"]
    )
    polygon_valid_path: str = Field(
        default="input/polygon_valid.geojson",
        examples=["input/polygon_valid.geojson", "input/run1/polygon_valid.geojson"]
    )

    @field_validator("config_valid_path", "input_valid_path", "polygon_valid_path")
    @classmethod
    def _inside_input_dir(cls, value: str) -> str:
        # Only input/ is mounted in the forecast container; the value is also a docker argument.
        parts = PurePosixPath(value).parts
        if value.startswith("-") or len(parts) < 2 or parts[0] != "input" or ".." in parts:
            raise ValueError("must be a file path under input/, e.g. input/config_valid.json")
        return value


class JobStatus(BaseModel):
    status: str = Field(examples=["running", "success", "error"])
    job_id: str = Field(examples=["forecast_a1b2c3d4"])
    started: str | None = Field(default=None, examples=["2024-01-15T10:30:00"])
    completed: str | None = Field(default=None, examples=["2024-01-15T10:35:00"])
    logs: str | None = Field(default=None, examples=["Processing step 1... OK"])
    message: str | None = Field(default=None, examples=["Pipeline completed"])
