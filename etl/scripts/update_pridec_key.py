from config import DHIS_TOKEN, DHIS_URL, dryRun, setup_logging, check_envvars
from pivot_dhis_tools import pridec_update_key
import os
import json

import logging

setup_logging()

logger = logging.getLogger("update_key")

check_envvars(required_vars = {
            'DHIS_TOKEN': DHIS_TOKEN,
            'DHIS_URL': DHIS_URL})

logger.info("Updating PRIDE-C key on %s", DHIS_URL)

pridec_update_key(dhis_url=DHIS_URL, token = DHIS_TOKEN, dryRun=dryRun)