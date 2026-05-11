def print_help():
    print(f"""
Task: calc_CSB_alerts

Usage:
-   Estimates the number of health facilities expecting more usage than average of prior three years and
          posts this information to the PRIDE-C instance

Notes:
-   This currently runs only on the Pivot PRIDE-C instance due to specific configurations.
""")

parser = argparse.ArgumentParser(add_help=False)  # disable default help
parser.add_argument("--help", "-h", action="store_true")

args = parser.parse_args()

if args.help:
    print_help()
    exit(0)

from config import DHIS_TOKEN, DHIS_URL, dryRun, setup_logging, check_envvars
from pivot_dhis_tools import post_dataElements, pridec_calc_CSB_alerts
import os
import json

import logging

setup_logging()

logger = logging.getLogger("calc_CSB_alerts")

logger.info("Estimating and POSTing 'CSB en vigilance' on %s", DHIS_URL)

check_envvars(required_vars = {
            'DHIS_TOKEN': DHIS_TOKEN,
            'DHIS_URL': DHIS_URL})

#automatically does for current month
json_alert = pridec_calc_CSB_alerts(dhis_url = DHIS_URL,
                                token = DHIS_TOKEN)

post_dataElements(dhis_url = DHIS_URL, payload = json_alert,
                   token= DHIS_TOKEN, dryRun=dryRun)