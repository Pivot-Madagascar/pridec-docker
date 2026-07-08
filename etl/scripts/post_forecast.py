from pivot_dhis_tools import post_dataElements
import os
import json
import logging

def print_help():
    print(f"""
Task: post_forecast

Usage:
-   POSTs a forecast in the form of output/forecast.json to the PRIDE-C instance

Notes:
-   None
""")

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(add_help=False)  # disable default help
    parser.add_argument("--help", "-h", action="store_true")
    return parser.parse_args()

def post_forecast():
    from etl.scripts.config import DHIS_TOKEN, DHIS_URL, dryRun, setup_logging, check_envvars

    setup_logging()

    logger = logging.getLogger("post_forecasts")

    check_envvars(required_vars = {
                'DHIS_TOKEN': DHIS_TOKEN,
                'DHIS_URL': DHIS_URL})

    logger.info("Posting forecasts to %s", DHIS_URL)

    output_dir = os.path.join(os.getcwd(), 'output')
    os.makedirs(output_dir, exist_ok=True)

    try:
        os.chmod(output_dir, 0o755)
    except PermissionError:
        pass

    try:
        with open('output/forecast.json', 'r') as file:
            json_payload = json.load(file)
    except FileNotFoundError as e:
            logger.error("The file 'output/forecast.json' was not found. Run the forecast step first.")
            raise e

    post_dataElements(dhis_url = DHIS_URL, payload = json_payload,
                       token= DHIS_TOKEN, dryRun=dryRun)

if __name__ == "__main__":
    args = parse_args()
    if args.help:
        print_help()
        exit(0)
    post_forecast()

