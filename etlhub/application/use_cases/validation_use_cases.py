import json
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd

from etl.scripts.validate_inputs import validate_inputs as _validate_inputs

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _check_external_data_level(external_data: pd.DataFrame | None, disease_data: pd.DataFrame) -> None:
    """The fkt and csb files have the same columns: only their orgUnits tell the level. None in common with the
    disease data = the other level's file, and every external covariate of the forecast would be empty."""
    if external_data is None or "orgUnit" not in external_data or "orgUnit" not in disease_data:
        return  # no file, or no orgUnit column: etl's validate_inputs reports it
    if not set(external_data["orgUnit"]) & set(disease_data["orgUnit"]):
        raise ValueError("external_data.csv shares no orgUnit with disease_data.json: is it the file of the other "
                         "level (fkt for a CSB run, or csb for an ADJ/COM run)? Every external covariate would be empty.")


def validate_input_files(
    config_path: str | None = None,
    external_data_path: str | None = None,
    disease_data_path: str | None = None,
    climate_data_path: str | None = None,
    orgunit_poly_path: str | None = None,
    input_dir: str | None = None,
) -> None:
    """Validates the forecast inputs and writes the *_valid files next to them. Its output is the job log."""
    # Paths are relative to the repo root (the API only accepts paths under input/), not to the worker's cwd.
    input_base = PROJECT_ROOT / (input_dir or "input")

    paths = {
        "config": str(PROJECT_ROOT / (config_path or input_base / "config.json")),
        "external_data": str(PROJECT_ROOT / (external_data_path or input_base / "external_data.csv")),
        "disease_data": str(PROJECT_ROOT / (disease_data_path or input_base / "disease_data.json")),
        "climate_data": str(PROJECT_ROOT / (climate_data_path or input_base / "climate_data.json")),
        "orgunit_poly": str(PROJECT_ROOT / (orgunit_poly_path or input_base / "orgUnit_poly.geojson")),
    }

    for p in [paths["config"], paths["disease_data"], paths["climate_data"], paths["orgunit_poly"]]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Required input file not found: {p}")

    with open(paths["config"]) as f:
        config_json = json.load(f)

    with open(paths["disease_data"]) as f:
        disease_data = pd.DataFrame(json.load(f)["dataValues"])

    with open(paths["climate_data"]) as f:
        climate_data = pd.DataFrame(json.load(f)["dataValues"])

    orgunit_poly = gpd.read_file(paths["orgunit_poly"])
    external_data = pd.read_csv(paths["external_data"]) if os.path.exists(paths["external_data"]) else None
    _check_external_data_level(external_data, disease_data)

    result = _validate_inputs(
        config=config_json,
        disease_data=disease_data,
        climate_data=climate_data,
        orgunit_poly=orgunit_poly,
        external_data=external_data,
    )

    with open(str(input_base / "config_valid.json"), "w") as f:
        json.dump(result.config, f, indent=2)

    result.input_data.to_json(str(input_base / "input_valid.json"), orient="records", indent=2)

    result.graph_poly.to_file(str(input_base / "polygon_valid.geojson"), driver="GeoJSON")

    print("All inputs valid.")
    print(f"Validated config saved to: {input_base / 'config_valid.json'}")
    print(f"Validated data saved to: {input_base / 'input_valid.json'}")
    print(f"Validated polygons saved to: {input_base / 'polygon_valid.geojson'}")
