from config import DHIS_TOKEN, DHIS_URL, dryRun, setup_logging
from pivot_dhis_tools import post_dataElements
import os
import json

import logging

setup_logging()

logger = logging.getLogger("post_forecasts")

logger.info("Posting forecasts to %s", DHIS_URL)

with open('output/forecast.json', 'r') as file:
    json_payload = json.load(file)

post_dataElements(dhis_url = DHIS_URL, payload = json_payload,
                   token= DHIS_TOKEN, 
                      dryRun=True)