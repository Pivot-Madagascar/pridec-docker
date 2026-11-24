"""calc_orgunit_alerts job (the "Alert thresholds (CSB only)" step of a CSB run): the number of orgUnits on alert,
written to output/alerts.json, which post_forecast then posts with the forecast.

etlhub's copy of etl/scripts/calc_orgUnit_alerts.py, which cannot run as it is (code at import, and it imports
DHIS_TOKEN / DHIS_URL / dryRun from config, names that no longer exist). Same computation: pivot_dhis_tools compares,
per orgUnit, the forecast's mean over 3 months with the mean of the same months over the 3 prior years, from the run's
own files (input/disease_data.json, output/forecast.json): no DHIS2 request, nothing posted here.
The context is the run's (OU_LEVEL, DISEASE_CODE, ALERT_NAME: pipeline.run_context) and the pass's (PARENT_OU); the
files are the mode's (test/input, test/output in test mode). The focal month is config.json's forecast_start (the months
the forecast covers; etlhub writes the pass's cycle there), else the current month, as the script.
ponytail: two copies of the same steps; a change to one must be made to the other.
"""
import json
import logging
from datetime import date, datetime

from pivot_dhis_tools import pridec_calc_orgUnit_alerts
from etl.scripts import config
from etl.scripts.config import check_envvars, get_disease_code, get_ou_level, get_parent_ou, setup_logging
from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir

logger = logging.getLogger("calc_orgUnit_alerts")


def _read(path):
    with open(path) as file:
        return json.load(file)


def _focal_date(config_json: dict) -> date:
    start = config_json.get("forecast_start")
    return datetime.strptime(str(start), "%Y%m").date() if start else date.today()


def calc_orgunit_alerts() -> None:
    setup_logging()  # here, not at import: the job's stdout/stderr redirection must be active
    parent_ou, ou_level, disease_code = get_parent_ou(), get_ou_level(), get_disease_code()
    alert_name = config._get("ALERT_NAME")  # the run's: set for CSB runs only
    check_envvars({"PARENT_OU": parent_ou, "OU_LEVEL": ou_level, "DISEASE_CODE": disease_code, "ALERT_NAME": alert_name})
    root, test_mode = get_settings().data_dir, current_test_mode()
    inputs, output = work_dir(root, "input", test_mode), work_dir(root, "output", test_mode)
    historic, forecast = _read(inputs / "disease_data.json"), _read(output / "forecast.json")
    focal = _focal_date(_read(inputs / "config.json"))

    logger.info("Estimating orgUnits on alert at level %s below parent %s for %s beginning %s",
                ou_level, parent_ou, disease_code, focal)
    alerts = pridec_calc_orgUnit_alerts(dhis_url=None, parent_ou=parent_ou, ou_level=int(ou_level),
                                        disease_code=disease_code.replace("pridec_historic_", ""),
                                        forecast_json=forecast, historic_json=historic, alert_name=alert_name,
                                        focal_date=focal)
    with open(output / "alerts.json", "w") as file:
        json.dump(alerts, file, indent=2)
    logger.info("Successfully created alert %s and saved in output/alerts.json: %s", alert_name, alerts.get("dataValues"))
