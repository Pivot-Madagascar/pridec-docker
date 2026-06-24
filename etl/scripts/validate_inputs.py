from typing import Any
from dataclasses import dataclass
from datetime import date
import argparse
import json
import geopandas as gpd
import pandas as pd
import logging


# --------------------------------------------------------------------------
# Classes 
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    def __init__(self, errors: list[str], messages: list[str]):
        self.errors = errors
        self.messages = messages

@dataclass
class ValidationResult:
    success: bool
    messages: list[str]
    config: dict
    input_data: pd.DataFrame
    graph_poly: gpd.GeoDataFrame

# ---------------------------------------------------------------------------
# Helper fx
# ---------------------------------------------------------------------------

def missing_columns(input_data: pd.DataFrame, column_names: list[str]) -> list[str]:
    """Return the names of required columns that are absent from *input_data*."""
    return [c for c in column_names if c not in input_data.columns]



def load_inputs(args):
    with open(args.config) as f:
        config = json.load(f)

    external_data = pd.read_csv(args.external_data) if args.external_data else None

    with open(args.disease_data) as f:
        disease_data = pd.DataFrame(json.load(f)["dataValues"])

    with open(args.climate_data) as f:
        climate_data = pd.DataFrame(json.load(f)["dataValues"])

    orgunit_poly = gpd.read_file(args.orgunit_poly)

    return config, external_data, disease_data, climate_data, orgunit_poly

def print_help():
    print(f"""
Task: validate_inputs

Usage:
-   Validates input data for PRIDE-C forecast
          
Notes:
-   Inputs should be stored in an input/ folder with the following requirements:      
          
    config.json:
        json file of forecast configurations. Required keys:
 
        * ``pred_vars``        – list of predictor variable names
        * ``model_weights``    – DataFrame with columns ``model`` and ``weight``
        * ``inla_hyper``       – dict of INLA hyper-parameters (optional)
        * ``ranger_hyper``     – dict of ranger hyper-parameters (optional)
        * ``quantile_levels``  – list/array of length 3
        * ``month_analysis``   – int
        * ``month_assess``     – int
        * ``month_lag``        – int (defaults to 3)
        * ``forecast_start``   – date string in ``YYYYMM`` format (defaults to
                                  current month)
    disease_data.json:
        DataFrame with columns ``orgUnit``, ``period``, ``dataElement``,
        ``value``.
    climate_data.json:
        DataFrame with columns ``orgUnit``, ``period``, ``dataElement``,
        ``value``.
    orgunit_poly.geojson:
        GeoDataFrame with at least an ``orgUnit`` column.
    external_data.csv:
        Optional DataFrame with columns ``orgUnit``, ``period``, and any
        predictor variables specified in ``config``.
""")


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

def validate_inputs(
    config: dict[str, Any],
    disease_data: pd.DataFrame,
    climate_data: pd.DataFrame,
    orgunit_poly: gpd.GeoDataFrame,
    external_data: pd.DataFrame | None = None
) -> bool | dict[str, Any]:
    """Validate input data for a PRIDE-C forecasting workflow.

    Parameters
    ----------
    config:
        Dictionary of forecast configurations. Required keys:

        * ``pred_vars``        – list of predictor variable names
        * ``model_weights``    – DataFrame with columns ``model`` and ``weight``
        * ``inla_hyper``       – dict of INLA hyper-parameters (optional)
        * ``ranger_hyper``     – dict of ranger hyper-parameters (optional)
        * ``quantile_levels``  – list/array of length 3
        * ``month_analysis``   – int
        * ``month_assess``     – int
        * ``month_lag``        – int (defaults to 3)
        * ``forecast_start``   – date string in ``YYYYMM`` format (defaults to
                                  current month)

    disease_data:
        DataFrame with columns ``orgUnit``, ``period``, ``dataElement``,
        ``value``.
    climate_data:
        DataFrame with columns ``orgUnit``, ``period``, ``dataElement``,
        ``value``.
    orgunit_poly:
        GeoDataFrame with at least an ``orgUnit`` column.
    external_data:
        Optional DataFrame with columns ``orgUnit``, ``period``, and any
        predictor variables specified in ``config``.
    return_inputs:
        If ``True``, return a dict of validated / processed inputs instead of
        ``True``.

    Returns
    -------
    ``True`` on success, ``False`` on error.
    """

    errors: list[str] = []
    messages: list[str] = []

    # ------------------------------------------------------------------ #
    # Check configurations                                                 #
    # ------------------------------------------------------------------ #

    expected_models = {"inla", "glm_nb", "ranger", "arimax", "naive"}
    present_models = {item["model"] for item in config.get("model_weights", [])}

    missing_model_weights = expected_models - present_models
    if missing_model_weights:
        errors.append("ERROR in config: missing the following model weights: "
            + ", ".join(sorted(missing_model_weights))
            + ". Supply a weight of `0` for models you don't want to include.")

    # inla_hyper --------------------------------------------------------
    if config.get("inla_hyper") is None:
        messages.append("No inla_hyper provided. Setting to default values.")
        config["inla_hyper"] = {
            "prec.unstruct": (1, 5e-4),
            "prec.spatial": (1, 5e-4),
            "prec.timerw1": (1, 0.01),
        }
    else:
        required_keys = {"prec.unstruct", "prec.spatial", "prec.timerw1"}
        hyper = config["inla_hyper"]
        keys_ok = set(hyper.keys()) == required_keys
        lens_ok = all(len(v) == 2 for v in hyper.values())
        types_ok = all(
            all(isinstance(x, (int, float)) for x in v) for v in hyper.values()
        )
        if not (keys_ok and lens_ok and types_ok):
            errors.append( "ERROR in config: `inla_hyper` poorly specified."
                "`prec.unstruct`, `prec.spatial`, `prec.timerw1` should each be "
                "numeric sequences of length 2."
            )
    # ranger_hyper ------------------------------------------------------
    if config.get("ranger_hyper") is None:
        messages.append("No ranger_hyper provided. Setting to default values.")
        config["ranger_hyper"] = {
            "mtry": None,
            "min.node.size": None,
            "num.trees": 500,
        }
    else:
        required_ranger_keys = {"mtry", "min.node.size", "num.trees"}
        if set(config["ranger_hyper"].keys()) != required_ranger_keys:
            errors.append(
                "ERROR in config: `ranger_hyper` poorly specified. Should include `mtry`, `min.node.size`, `num.trees`."
            )

    # quantile_levels ---------------------------------------------------
    if len(config.get("quantile_levels", [])) != 3:
        errors.append("ERROR in config: Quantile levels must be a sequence of length 3.")

    # month_analysis ----------------------------------------------------
    if not isinstance(config.get("month_analysis"), int):
        errors.append("ERROR in config: month_analysis must be an integer of length 1.")

    # month_assess ------------------------------------------------------
    if not isinstance(config.get("month_assess"), int):
        errors.append("ERROR in config: month_assess must be an integer of length 1.")

    # month_lag ---------------------------------------------------------
    if config.get("month_lag") is None:
        messages.append("No month_lag provided. Setting to default of 3.")
        config["month_lag"] = 3

    # forecast_start ----------------------------------------------------
    if config.get("forecast_start") is None:
        today = date.today()
        config["forecast_start"] = f"{today.year}{today.month:02d}"
        messages.append("No forecast_start provided. Setting to current month.")

    try:
        pd.to_datetime(config["forecast_start"] + "01", format="%Y%m%d")
    except (ValueError, TypeError):
        errors.append("ERROR in config: forecast_start is not a valid date. "
                      "Is it in YYYYMM format?"
        )

    # ------------------------------------------------------------------ #
    # Ensure appropriate columns in all datasets                          #
    # ------------------------------------------------------------------ #

    # external_data columns --------------------------------------------
    if external_data is not None:
        missing = missing_columns(external_data, ["orgUnit", "period"])
        if missing:
            errors.append(
                "ERROR: Columns missing from external_data: "
                + ", ".join(missing)
            )

    # disease_data columns ---------------------------------------------
    required_disease = ["orgUnit", "period", "dataElement", "value"]
    missing = missing_columns(disease_data, required_disease)
    if missing:
        errors.append(
            "ERROR: Columns missing from disease_data: " + ", ".join(missing)
        )

    # climate_data columns --------------------------------------------
    required_climate = ["orgUnit", "period", "dataElement", "value"]
    missing = missing_columns(climate_data, required_climate)
    if missing:
        errors.append(
            "ERROR: Columns missing from climate_data: " + ", ".join(missing)
        )

    # orgunit_poly columns -------------------------------------------
    missing = missing_columns(orgunit_poly, ["orgUnit"])
    if missing:
        errors.append(
            "\nERROR: Columns missing from orgunit_poly: " + ", ".join(missing)
        )

    # Coerce period to str in all datasets ---------------------------
    if external_data is not None:
        external_data = external_data.copy()
        external_data["period"] = external_data["period"].astype(str)

    disease_data = disease_data.copy()
    disease_data["period"] = disease_data["period"].astype(str)

    climate_data = climate_data.copy()
    climate_data["period"] = climate_data["period"].astype(str)

    # Store disease element in config --------------------------------
    config["disease_dataElement"] = disease_data["dataElement"].unique().tolist()

    # ------------------------------------------------------------------ #
    # External data – NA check                                            #
    # ------------------------------------------------------------------ #

    if external_data is not None:
        na_counts = external_data.isna().sum()
        na_cols = na_counts[na_counts > 0]
        if not na_cols.empty:
            errors.append(
                "ERROR: External data has `NA` in the following columns: "
                + ", ".join(na_cols.index.tolist())
            )

    # ------------------------------------------------------------------ #
    # Disease data checks                                                 #
    # ------------------------------------------------------------------ #

    disease_data = disease_data[["orgUnit", "period", "dataElement", "value"]]

    if disease_data["dataElement"].nunique() > 1:
        errors.append(
            "ERROR: `disease_data` should contain one dataElement but contains "
            "multiple:\n"
            + ", ".join(disease_data["dataElement"].unique().tolist())
        )

    #check the types are numeric and strings
    expected_dtypes = {
        "orgUnit": "object",
        "period": "object",
        "dataElement": "object",
        "value": "float",
    }
    for col, expected in expected_dtypes.items():
        actual = disease_data[col].dtype
        if expected == "float" and not pd.api.types.is_numeric_dtype(actual):
            errors.append(f"ERROR: `disease_data` column `{col}` should be numeric but is {actual}.")
        elif expected == "object" and not pd.api.types.is_string_dtype(actual):
            errors.append(f"ERROR: `disease_data` column `{col}` should be string/object but is {actual}."
            )

    # ------------------------------------------------------------------ #
    # Combine into input_data and check predictor variables               #
    # ------------------------------------------------------------------ #

    ext_cols = list(external_data.columns) if external_data is not None else []
    climate_elements = climate_data["dataElement"].unique().tolist()
    available_vars = climate_elements + ext_cols

    missing_pred_vars = [
        v for v in config.get("pred_vars", []) if v not in available_vars
    ]

    if missing_pred_vars:
        errors.append(
            "ERROR: The following predictor variables are missing from the input datasets:"
            + ", ".join(missing_pred_vars)
            + ". Ensure they are present in `climate_data` or `external_data`."
        )
        input_data = None
    else:
        combined = pd.concat([disease_data, climate_data], ignore_index=True)
        input_data = combined.pivot_table(
            index=["orgUnit", "period"],
            columns="dataElement",
            values="value",
            aggfunc="first",
        ).reset_index()
        input_data.columns.name = None

        if external_data is not None:
            input_data = input_data.merge(
                external_data, on=["orgUnit", "period"], how="outer"
            )

        # Keep only orgUnits that appear in disease_data
        valid_orgunits = disease_data["orgUnit"].unique()
        input_data = input_data[input_data["orgUnit"].isin(valid_orgunits)]

        # Limit columns
        keep_cols = (
            ["orgUnit", "period"]
            + config["disease_dataElement"]
            + config["pred_vars"]
        )
        input_data = input_data[[c for c in keep_cols if c in input_data.columns]]

    # ------------------------------------------------------------------ #
    # Polygon checks                                                      #
    # ------------------------------------------------------------------ #

    orgunit_poly = orgunit_poly.copy()
    orgunit_poly["org_ID"] = range(1, len(orgunit_poly) + 1)

    if input_data is not None:
        all_ou = input_data["orgUnit"].unique()
        missing_org_poly = [
            ou for ou in all_ou if ou not in orgunit_poly["orgUnit"].values
        ]
        if missing_org_poly:
            errors.append(
                "ERROR: The following orgUnits are missing corresponding polygons in `orgunit_poly`:"
                + "\n".join(missing_org_poly)
            )

    # ------------------------------------------------------------------ #
    # Return                                                               #
    # ------------------------------------------------------------------ #

    # on error:
    if errors:
        raise ValidationError(errors=errors, messages=messages)

    # on success:
    return ValidationResult(success=True, messages=messages, config = config, 
                            input_data = input_data, graph_poly = orgunit_poly)

    

if __name__ == "__main__":
    from config import setup_logging
    setup_logging()
    logger = logging.getLogger("validate_inputs")

    parser = argparse.ArgumentParser(add_help=False)  # disable default help
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--config", required=False, default = "input/config.json")
    parser.add_argument("--external_data", required=False, default = "input/external_data.csv") #to debug
    parser.add_argument("--disease_data", required=False, default = "input/disease_data.json")
    parser.add_argument("--climate_data", required=False, default = "input/climate_data.json")
    parser.add_argument("--orgunit_poly", required=False, default = "input/orgUnit_poly.geojson")

    args = parser.parse_args()
    
    if args.help:
        print_help()
        exit(0)

    config, external_data, disease_data, climate_data, orgunit_poly = load_inputs(args)
    
    try:
        result = validate_inputs(
            config=config,
            external_data=external_data,
            disease_data=disease_data,
            climate_data=climate_data,
            orgunit_poly=orgunit_poly
        )
        for msg in result.messages:
            logger.info(msg)
        logger.info("SUCCESS: All inputs valid.")
        # save the validated and formatted inputs to be directly used by forecast function
        with open("input/config_valid.json", "w") as f:
            json.dump(result.config, f, indent=2)
        logger.info(f"Validated config saved to input/config_valid.json")

        result.input_data.to_json("input/input_valid.json", orient="records", indent=2)
        logger.info("Validated input data saved to input/input_valid.json")

        result.graph_poly.to_file("input/polygon_valid.geojson", driver="GeoJSON")
        logger.info("Validated orgUnit polygons saved to input/polygon_valid.geojson")

    except ValidationError as e:
        for msg in e.messages:
            logger.info(msg)
        for err in e.errors:
            logger.error(err)
        exit(1)