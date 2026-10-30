import argparse

def print_help():
    print(f"""
Task: import_pivot_COM

Usage:
-   Import disease cases reported at community health sites during prior eight months from Pivot DHIS2 instance to PRIDE-C instance

Notes:
-   This requires `PIVOT_URL` and `PIVOT_TOKEN` in .env
-   Will flag potentially erroneous values (negative, NAN, >100) and require user approval to post.
""")

parser = argparse.ArgumentParser(add_help=False)  # disable default help
parser.add_argument("--help", "-h", action="store_true")

args = parser.parse_args()

if args.help:
    print_help()
    exit(0)


from config import DHIS_TOKEN, DHIS_URL, PIVOT_URL, PIVOT_TOKEN, dryRun, setup_logging, check_envvars
from requests.auth import HTTPBasicAuth
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import logging
from pivot_dhis_tools import import_pivot_com

setup_logging()

logger = logging.getLogger("import_pivot_COM")

check_envvars(required_vars = {
            'DHIS_TOKEN': DHIS_TOKEN,
            'DHIS_URL': DHIS_URL,
            'PIVOT_TOKEN': PIVOT_TOKEN,
            'PIVOT_URL': PIVOT_URL,
        }
)


logger.info("Importing COM Case Data from %s into %s", PIVOT_URL, DHIS_URL)

import_pivot_com(dhis_url=DHIS_URL,
                 dhis_token=DHIS_TOKEN,
                 pivot_url=PIVOT_URL,
                 pivot_token=PIVOT_TOKEN,
                 dryRun = dryRun)