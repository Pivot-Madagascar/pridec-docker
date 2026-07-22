import argparse

def print_help():
    print(f"""
Task: post_forecast

Usage:
-   POSTs a forecast in the form of output/forecast.json to the PRIDE-C instance
-   POSTs calculated PRIDE-C Alerts from output/alerts.json to the PRIDE-C instance

Notes:
-   None
""")

parser = argparse.ArgumentParser(add_help=False)  # disable default help
parser.add_argument("--help", "-h", action="store_true")

args = parser.parse_args()

if args.help:
    print_help()
    exit(0)

from config import DHIS_TOKEN, DHIS_URL, dryRun, setup_logging, check_envvars
from pivot_dhis_tools import post_dataElements
import os
import json

import logging

setup_logging()

logger = logging.getLogger("post_forecasts")


check_envvars(required_vars = {
            'DHIS_TOKEN': DHIS_TOKEN,
            'DHIS_URL': DHIS_URL})

logger.info("Posting forecasts to %s", DHIS_URL)

forecast_payload = None
alert_payload = None

try:
    with open('output/forecast.json', 'r') as file:
        forecast_payload = json.load(file)
except FileNotFoundError:
        logger.warning("The file 'output/forecast.json' was not found and will not be posted. Run the forecast step first.")

if forecast_payload is not None: 
    post_dataElements(dhis_url = DHIS_URL, payload = forecast_payload,
                    token= DHIS_TOKEN, dryRun=dryRun)

logger.info("Posting alerts to %s", DHIS_URL)

try:
    with open('output/alerts.json', 'r') as file:
        alert_payload = json.load(file)
except FileNotFoundError:
        logger.warning("The file 'output/alerts.json' was not found and will not be posted. Run the calc_orgUnit_alerts step first")

if alert_payload is not None: 
    post_dataElements(dhis_url = DHIS_URL, payload = alert_payload,
                    token= DHIS_TOKEN, dryRun=dryRun)


