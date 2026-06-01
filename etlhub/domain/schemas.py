from pydantic import BaseModel, Field


class ETLResponse(BaseModel):
    status: str = ""
    message: str = ""
    job_id: str = ""


class ForecastParams(BaseModel):
    config_path: str = Field(default="input/config.json")
    external_data_path: str = Field(default="input/external_data.csv")
    climate_data_path: str = Field(default="input/climate_data.json")
    disease_data_path: str = Field(default="input/disease_data.json")
    orgUnit_poly_path: str = Field(default="input/orgUnit_poly.geojson")


class JobStatus(BaseModel):
    status: str
    job_id: str
    started: str | None = None
    completed: str | None = None
    logs: str | None = None
    message: str | None = None