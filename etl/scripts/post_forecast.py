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

try:
    with open('output/forecast.json', 'r') as file:
        json_payload = json.load(file)
except FileNotFoundError as e:
        logger.error("The file 'output/forecast.json' was not found. Run the forecast step first.")
        raise SystemExit(1) from e

post_dataElements(dhis_url = DHIS_URL, payload = json_payload,
                   token= DHIS_TOKEN, dryRun=True)