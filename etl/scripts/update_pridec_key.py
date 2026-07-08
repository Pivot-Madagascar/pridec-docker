from pivot_dhis_tools import pridec_update_key
import os
import json
import logging

def print_help():
    print(f"""
Task: update_pridec_key

Usage:
-   Updates a PRIDE-C key in teh datastore that is used to signal a local cache to re-download data.
           
Notes:
-   Should be run after a monthly update
""")

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(add_help=False)  # disable default help
    parser.add_argument("--help", "-h", action="store_true")
    return parser.parse_args()

def update_key():
    from etl.scripts.config import DHIS_TOKEN, DHIS_URL, dryRun, setup_logging, check_envvars

    setup_logging()

    logger = logging.getLogger("update_key")

    check_envvars(required_vars = {
                'DHIS_TOKEN': DHIS_TOKEN,
                'DHIS_URL': DHIS_URL})

    logger.info("Updating PRIDE-C key on %s", DHIS_URL)

    pridec_update_key(dhis_url=DHIS_URL, token = DHIS_TOKEN, dryRun=dryRun)

if __name__ == "__main__":
    args = parse_args()
    if args.help:
        print_help()
        exit(0)
    update_key()