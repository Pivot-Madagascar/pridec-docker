from pydantic import BaseModel, Field


class ETLResponse(BaseModel):
    status: str = Field(default="", examples=["accepted", "success", "error"])
    message: str = Field(default="", examples=["Task started in background", "Job completed successfully"])
    job_id: str = Field(default="", examples=["import_gee_a1b2c3d4", "forecast_x7y8z9w0"])
    webhook_url: str | None = Field(default=None, examples=["https://callback.example.com/webhook"])


class ElementAvailability(BaseModel):
    """One dataElement of an import. Counts are orgUnits with a value, per period (YYYYMM)."""
    code: str = Field(examples=["pridec_historic_COMMalaria"])
    raw: dict[str, int] | None = Field(default=None, description="Stored values (/api/dataValueSets); null if the query failed")
    analytics: dict[str, int] | None = Field(default=None, description="Values in the analytics tables; null if the query failed")
    last_updated: str | None = Field(default=None, description="Latest lastUpdated of the stored values")
    imported: bool = Field(default=False, description="A stored value for every period")
    analytics_up_to_date: bool | None = Field(default=None, description="analytics == raw; null if one query failed")
    error: str | None = None


class ImportAvailability(BaseModel):
    task: str = Field(examples=["import_gee", "import_pivot_com", "import_pivot_csb"])
    periods: list[str] = Field(examples=[["202607", "202608", "202609"]])
    org_units: str = Field(examples=["ou:LEVEL-6;VtP4BdCeXIo"])
    elements: list[ElementAvailability]
    checked_at: str = Field(description="When this section's check started, etlhub local time (as the journal)")
    checked_by: str | None = Field(default=None, description="DHIS2 username of who checked it")
    pass_id: str | None = Field(default=None, description="Pass it was checked in; null before the month's first launch")
    reused: bool = Field(description="True: checked earlier in the cycle and still valid, DHIS2 not asked now")


class ImportAvailabilityReport(BaseModel):
    dhis_url: str
    last_analytics: str | None = Field(default=None, description="lastAnalyticsTableSuccess of DHIS2 (server local time), "
                                       "read by the latest check of the report's sections")
    imports: list[ImportAvailability]

