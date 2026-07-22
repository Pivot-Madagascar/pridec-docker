import argparse

def print_help():
    print(f"""
Task: calc_orgUnit_alerts

Usage:
-   Estimates the number of orgUnits expecting more usage than average of prior three years and
          saves to output/alerts.json
""")

parser = argparse.ArgumentParser(add_help=False)  # disable default help
parser.add_argument("--help", "-h", action="store_true")

args = parser.parse_args()

if args.help:
    print_help()
    exit(0)

from config import DHIS_TOKEN, DHIS_URL, dryRun, setup_logging, check_envvars, PARENT_OU, OU_LEVEL, DISEASE_CODE, ALERT_NAME
from pivot_dhis_tools import post_dataElements, pridec_calc_orgUnit_alerts
import os
import json

import logging

setup_logging()

logger = logging.getLogger("calc_orgUnit_alerts")

logger.info("Estimating orgUnits on alert at level %s below parent %s for %s", OU_LEVEL, PARENT_OU, DISEASE_CODE)

check_envvars(required_vars = {
            'PARENT_OU': PARENT_OU,
            'OU_LEVEL': OU_LEVEL,
            'DISEASE_CODE': DISEASE_CODE})

#load local data by default
with open("input/disease_data.json") as f:
    historic_json = json.load(f)

with open("output/forecast.json") as f:
    forecast_json = json.load(f)

disease_code_short = DISEASE_CODE.replace("pridec_historic_", "")

#automatically does for current month
json_alert = pridec_calc_orgUnit_alerts(dhis_url = DHIS_URL, 
                                        parent_ou = PARENT_OU,
                                        ou_level = OU_LEVEL,
                                        disease_code = disease_code_short,
                                        forecast_json = forecast_json,
                                        historic_json = historic_json,
                                        alert_name = ALERT_NAME,
                                        token = DHIS_TOKEN)


with open("output/alerts.json", "w") as f:
    json.dump(json_alert, f, indent=2)