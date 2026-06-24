import io
import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from etlhub.domain.schemas.validation import ValidationResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "etl" / "scripts"))

from etl.scripts.validate_inputs import validate_inputs as _validate_inputs, ValidationError


def run_validate_inputs(
    config_path: str | None = None,
    external_data_path: str | None = None,
    disease_data_path: str | None = None,
    climate_data_path: str | None = None,
    orgunit_poly_path: str | None = None,
    input_dir: str | None = None,
    job_store=None,
    job_id=None,
) -> dict[str, Any]:
    from etlhub.application.use_cases.etl_use_cases import capture_stdout

    buf = None
    try:
        try:
            with capture_stdout(job_id=job_id) as buf:
                input_base = Path(input_dir or str(PROJECT_ROOT / "input"))

                paths = {
                    "config": config_path or str(input_base / "config.json"),
                    "external_data": external_data_path or str(input_base / "external_data.csv"),
                    "disease_data": disease_data_path or str(input_base / "disease_data.json"),
                    "climate_data": climate_data_path or str(input_base / "climate_data.json"),
                    "orgunit_poly": orgunit_poly_path or str(input_base / "orgUnit_poly.geojson"),
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

                return {
                    "status": "success",
                    "message": "All inputs valid.",
                    "config_path": str(input_base / "config_valid.json"),
                    "data_path": str(input_base / "input_valid.json"),
                    "polygons_path": str(input_base / "polygon_valid.geojson"),
                }
        except FileNotFoundError as e:
            print(f"FileNotFoundError: {e}")
            raise
        except Exception as e:
            print(f"Error during validation: {e}")
            raise
    finally:
        if job_store and job_id and buf is not None:
            job_store.save_logs(job_id, buf.getvalue())
