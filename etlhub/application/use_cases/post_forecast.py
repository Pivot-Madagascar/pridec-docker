"""POST /post_forecast: output/forecast.json, then output/alerts.json if present, to DHIS2.

etlhub's copy of etl/scripts/post_forecast.py, whose code runs at import (CLI only).
ponytail: two copies of the same steps; a change to one must be made to the other.
"""
import json
import logging

from pivot_dhis_tools import post_dataElements
from etl.scripts.config import get_dhis_token, get_dhis_url, get_dry_run, setup_logging

logger = logging.getLogger("post_forecasts")


def post_forecast() -> None:
    setup_logging()  # here, not at import: the job's stdout/stderr redirection must be active
    url, token, dry_run = get_dhis_url(), get_dhis_token(), get_dry_run()

    logger.info("Posting forecasts to %s", url)
    try:
        with open("output/forecast.json") as file:
            forecast = json.load(file)
    except FileNotFoundError:
        logger.error("The file 'output/forecast.json' was not found and will not be posted. Run the forecast step first.")
        raise
    post_dataElements(dhis_url=url, payload=forecast, token=token, dryRun=dry_run)

    logger.info("Posting alerts to %s", url)
    try:
        with open("output/alerts.json") as file:
            alerts = json.load(file)
    except FileNotFoundError:
        logger.warning("The file 'output/alerts.json' was not found and will not be posted. Run the calc_orgUnit_alerts step first.")
        return
    post_dataElements(dhis_url=url, payload=alerts, token=token, dryRun=dry_run)
