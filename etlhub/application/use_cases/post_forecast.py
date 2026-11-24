"""POST /post_forecast (a Celery job): output/forecast.json, then output/alerts.json if present, to DHIS2.

etlhub's copy of etl/scripts/post_forecast.py, whose code runs at import (CLI only).
ponytail: two copies of the same steps; a change to one must be made to the other.
"""
import json
import logging

from pivot_dhis_tools import post_dataElements
from etl.scripts import config
from etl.scripts.config import get_dhis_token, get_dhis_url, get_dry_run, setup_logging
from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir

logger = logging.getLogger("post_forecasts")


def post_forecast() -> str:
    """Returns the job's end message (the toast's): a CSB run posted without its alerts says so."""
    setup_logging()  # here, not at import: the job's stdout/stderr redirection must be active
    url, token, dry_run = get_dhis_url(), get_dhis_token(), get_dry_run()
    output = work_dir(get_settings().data_dir, "output", current_test_mode())  # test/output in test mode

    logger.info("Posting forecasts to %s", url)
    try:
        with open(output / "forecast.json") as file:
            forecast = json.load(file)
    except FileNotFoundError:
        logger.error("The file 'output/forecast.json' was not found and will not be posted. Run the forecast step first.")
        raise
    post_dataElements(dhis_url=url, payload=forecast, token=token, dryRun=dry_run)

    logger.info("Posting alerts to %s", url)
    try:
        with open(output / "alerts.json") as file:
            alerts = json.load(file)
    except FileNotFoundError:
        logger.warning("The file 'output/alerts.json' was not found and will not be posted. Run the calc_orgUnit_alerts step first.")
        # ALERT_NAME: the run's, set for CSB runs only; the others have no alerts to miss.
        if config._get("ALERT_NAME"):
            return "Forecast posted; the alert data was not included (no alerts.json: alerts skipped or not computed)"
        return "Forecast posted"
    post_dataElements(dhis_url=url, payload=alerts, token=token, dryRun=dry_run)
    return "Forecast and alerts posted"
