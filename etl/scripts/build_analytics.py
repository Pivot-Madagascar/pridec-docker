import argparse

def print_help():
    print(f"""
Task: build_analytics

Usage:
-   Builds analytics table on DHIS2 PRIDE-C instance. 

Notes:
-   Depending on the size of your instance, this can take some time. 
    Check the url for the `completed` status before running other steps.
""")

parser = argparse.ArgumentParser(add_help=False)  # disable default help
parser.add_argument("--help", "-h", action="store_true")

args = parser.parse_args()

if args.help:
    print_help()
    exit(0)

from config import DHIS_TOKEN, DHIS_URL,  setup_logging
from requests.auth import HTTPBasicAuth
import logging
from pivot_dhis_tools import launch_analytics

setup_logging()
logger = logging.getLogger("analytics")

logger.info("Launching analytics table at %s", DHIS_URL)

launch_analytics(dhis_url=DHIS_URL,
                 token=DHIS_TOKEN)