import json
import os

import geopandas as gpd
import pandas as pd

from etl.scripts.validate_inputs import validate_inputs as _validate_inputs
from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir


def _check_external_data_level(external_data: pd.DataFrame | None, disease_data: pd.DataFrame) -> None:
    """The fkt and csb files have the same columns: only their orgUnits tell the level. None in common with the
    disease data = the other level's file, and every external covariate of the forecast would be empty."""
    if external_data is None or "orgUnit" not in external_data or "orgUnit" not in disease_data:
        return  # no file, or no orgUnit column: etl's validate_inputs reports it
    if not set(external_data["orgUnit"]) & set(disease_data["orgUnit"]):
        raise ValueError("external_data.csv shares no orgUnit with disease_data.json: is it the file of the other "
                         "level (fkt for a CSB run, or csb for an ADJ/COM run)? Every external covariate would be empty.")


def _check_forecast_months(config: dict, input_data: pd.DataFrame) -> None:
    """The R forecast (PRIDEC::split_cv_forecast) needs the months forecast_start - month_analysis and
    forecast_start + month_assess - 1 in the data, else it stops in the forecast container. Refused here, with its cause.
    ponytail: checks input_valid's periods, as the R data prep kept them so far; follow split_cv_forecast if it changes."""
    start = pd.Period(year=int(config["forecast_start"][:4]), month=int(config["forecast_start"][4:6]), freq="M")
    periods = set(input_data["period"].astype(str))
    needed = [(start - config["month_analysis"]).strftime("%Y%m"), (start + config["month_assess"] - 1).strftime("%Y%m")]
    missing = [p for p in needed if p not in periods]
    if missing:
        raise ValueError(
            f"The data covers {min(periods, default='no month')} to {max(periods, default='no month')}, but the forecast of {start.strftime('%Y%m')} needs "
            f"{' and '.join(missing)} (month_analysis {config['month_analysis']}, month_assess {config['month_assess']}): "
            "the months of the grid come from disease_data, climate_data and external_data.csv; use an external_data "
            "that covers them, or change month_analysis / month_assess.")


def validate_input_files(
    config_path: str | None = None,
    external_data_path: str | None = None,
    disease_data_path: str | None = None,
    climate_data_path: str | None = None,
    orgunit_poly_path: str | None = None,
    input_dir: str | None = None,
) -> None:
    """Validates the forecast inputs and writes the *_valid files next to them. Its output is the job log."""
    # Paths are relative to the mode's root (the API only accepts paths under input/): DATA_DIR in production,
    # DATA_DIR/test in test mode, whose input/ is the test one.
    root = work_dir(get_settings().data_dir, "input", current_test_mode()).parent
    input_base = root / (input_dir or "input")

    # A given path is relative to root; a default is already under root (input_base): never join root twice, a
    # relative DATA_DIR (".") would give test/test/input.
    given = {"config": (config_path, "config.json"), "external_data": (external_data_path, "external_data.csv"),
             "disease_data": (disease_data_path, "disease_data.json"),
             "climate_data": (climate_data_path, "climate_data.json"),
             "orgunit_poly": (orgunit_poly_path, "orgUnit_poly.geojson")}
    paths = {k: str(root / path if path else input_base / default) for k, (path, default) in given.items()}

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
    _check_forecast_months(result.config, result.input_data)  # before writing: no *_valid file for a forecast that would fail

    with open(str(input_base / "config_valid.json"), "w") as f:
        json.dump(result.config, f, indent=2)

    result.input_data.to_json(str(input_base / "input_valid.json"), orient="records", indent=2)

    result.graph_poly.to_file(str(input_base / "polygon_valid.geojson"), driver="GeoJSON")

    print("All inputs valid.")
    print(f"Validated config saved to: {input_base / 'config_valid.json'}")
    print(f"Validated data saved to: {input_base / 'input_valid.json'}")
    print(f"Validated polygons saved to: {input_base / 'polygon_valid.geojson'}")
