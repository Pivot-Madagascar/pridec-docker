from pathlib import PurePosixPath
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def _inside_input_dir(value: str) -> str:
    # Only input/ is mounted in the forecast container; the value is also a docker argument.
    parts = PurePosixPath(value).parts
    if value.startswith("-") or len(parts) < 2 or parts[0] != "input" or ".." in parts:
        raise ValueError("must be a file path under input/, e.g. input/config_valid.json")
    return value


# Relative to the repo root, under input/. Used for request bodies and query parameters alike.
InputPath = Annotated[str, AfterValidator(_inside_input_dir)]


class ForecastParams(BaseModel):
    config_valid_path: InputPath = Field(
        default="input/config_valid.json",
        examples=["input/config_valid.json", "input/run1/config_valid.json"]
    )
    input_valid_path: InputPath = Field(
        default="input/input_valid.json",
        examples=["input/input_valid.json", "input/run1/input_valid.json"]
    )
    polygon_valid_path: InputPath = Field(
        default="input/polygon_valid.geojson",
        examples=["input/polygon_valid.geojson", "input/run1/polygon_valid.geojson"]
    )


class JobStatus(BaseModel):
    status: str = Field(examples=["running", "success", "error"])
    job_id: str = Field(examples=["forecast_a1b2c3d4"])
    started: str | None = Field(default=None, examples=["2024-01-15T10:30:00"])
    completed: str | None = Field(default=None, examples=["2024-01-15T10:35:00"])
    logs: str | None = Field(default=None, examples=["Processing step 1... OK"])
    message: str | None = Field(default=None, examples=["Pipeline completed"])
