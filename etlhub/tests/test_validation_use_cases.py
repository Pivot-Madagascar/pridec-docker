"""validate_inputs refuses an external_data of the other level (same columns, other orgUnits), on the repo's assets,
and a grid of months the R forecast would stop on."""
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from etlhub.application.use_cases.validation_use_cases import _check_external_data_level, _check_forecast_months

ASSETS = Path(__file__).resolve().parents[2] / "assets"


@pytest.fixture
def csb_disease_data():
    """The test disease data: the 21 CSB orgUnits."""
    return pd.DataFrame(json.loads((ASSETS / "test/inputs/disease_data.json").read_text())["dataValues"])


def test_the_external_data_of_the_same_level_passes(csb_disease_data):
    _check_external_data_level(pd.read_csv(ASSETS / "test/inputs/external_data.csv"), csb_disease_data)
    _check_external_data_level(pd.read_csv(ASSETS / "forecast_configs/external_data_csb.csv"), csb_disease_data)
    _check_external_data_level(None, csb_disease_data)  # no file: etl's validate_inputs decides


def test_the_external_data_of_the_other_level_is_refused(csb_disease_data):
    fkt = pd.read_csv(ASSETS / "forecast_configs/external_data_fkt.csv")

    with pytest.raises(ValueError, match="shares no orgUnit with disease_data.json"):
        _check_external_data_level(fkt, csb_disease_data)


def _grid(first: str, last: str) -> pd.DataFrame:
    return pd.DataFrame({"period": pd.period_range(first, last, freq="M").strftime("%Y%m")})


def test_a_grid_that_misses_a_forecast_month_is_refused():
    config = {"forecast_start": "202611", "month_analysis": 60, "month_assess": 3}
    # The test pass of 2026-11-25: assets/test/inputs/external_data.csv stopped the grid at 202612, R needed 202701.
    with pytest.raises(ValueError, match="needs 202701"):
        _check_forecast_months(config, _grid("2021-01", "2026-12"))
    with pytest.raises(ValueError, match="needs 202111"):  # forecast_start - month_analysis
        _check_forecast_months(config, _grid("2022-01", "2027-12"))
    _check_forecast_months(config, _grid("2015-01", "2027-12"))  # the production external data's months


@pytest.mark.parametrize("test_mode, folder", [(False, "input"), (True, "test/input")])
def test_the_inputs_are_read_in_the_mode_s_folder_under_data_dir(monkeypatch, tmp_path, test_mode, folder):
    from types import SimpleNamespace

    from etlhub.application.use_cases import validation_use_cases
    from etlhub.core.job_context import pipeline_test_mode
    monkeypatch.setattr(validation_use_cases, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    token = pipeline_test_mode.set(test_mode)
    try:
        with pytest.raises(FileNotFoundError, match=re.escape(str(tmp_path / folder / "config.json"))):
            validation_use_cases.validate_input_files()
        with pytest.raises(FileNotFoundError, match=re.escape(str(tmp_path / folder / "run1" / "config.json"))):
            validation_use_cases.validate_input_files(input_dir="input/run1")
    finally:
        pipeline_test_mode.reset(token)
