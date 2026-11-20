"""validate_inputs refuses an external_data of the other level (same columns, other orgUnits), on the repo's assets."""
import json

import pandas as pd
import pytest

from etlhub.application.use_cases.validation_use_cases import PROJECT_ROOT, _check_external_data_level

ASSETS = PROJECT_ROOT / "assets"


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
