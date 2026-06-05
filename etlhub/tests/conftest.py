import sys
import types
import pytest


@pytest.fixture
def job_store():
    from etlhub.infrastructure.job_store import JobStore
    JobStore._jobs.clear()
    return JobStore()


for _mod in [
    "pridec_gee",
    "pivot_dhis_tools",
    "etl.scripts.import_gee",
    "etl.scripts.import_pivot_COM",
    "etl.scripts.import_pivot_CSB",
    "etl.scripts.fetch_pridec_climate",
    "etl.scripts.fetch_pridec_disease",
    "etl.scripts.fetch_pridec_geojson",
    "etl.scripts.build_analytics",
    "etl.scripts.post_forecast",
    "etl.scripts.calc_CSB_alerts",
    "etl.scripts.update_pridec_key",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

for _mod, _attrs in {
    "pridec_gee": ["AVAILABLE_VARIABLES"],
    "pivot_dhis_tools": [],
    "etl.scripts.import_gee": ["import_gee"],
    "etl.scripts.import_pivot_COM": ["import_pivot_com"],
    "etl.scripts.import_pivot_CSB": ["import_pivot_csb"],
    "etl.scripts.fetch_pridec_climate": ["fetch_climate"],
    "etl.scripts.fetch_pridec_disease": ["fetch_disease"],
    "etl.scripts.fetch_pridec_geojson": ["fetch_geojson"],
    "etl.scripts.build_analytics": ["build_analytics"],
    "etl.scripts.post_forecast": ["post_forecast"],
    "etl.scripts.calc_CSB_alerts": ["calc_csb_alerts"],
    "etl.scripts.update_pridec_key": ["update_key"],
}.items():
    for _attr in _attrs:
        if not hasattr(sys.modules[_mod], _attr):
            setattr(sys.modules[_mod], _attr, lambda *a, **k: None)
