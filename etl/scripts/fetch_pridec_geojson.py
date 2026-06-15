import argparse

def print_help():
    print(f"""
Task: fetch_pridec_geojson

Usage:
-   Downloads geojson data of orgUnit polygons from DHIS2 instance and saves into `input` folder. 

Notes:
-   Geojson will be downloaded for the orgUnit level specified in .env via OU_LEVEL.
    Fokontany = 6. CSB = 5.
""")

parser = argparse.ArgumentParser(add_help=False)  # disable default help
parser.add_argument("--help", "-h", action="store_true")

args = parser.parse_args()

if args.help:
    print_help()
    exit(0)

from config import DHIS_TOKEN, DHIS_URL, OU_LEVEL, PARENT_OU, setup_logging, check_envvars
import logging
import json
import os

from pridec_gee import get_dhis_geojson

def fetch_geojson():
    setup_logging()

    logger = logging.getLogger("fetch_pridec_geojson")

    check_envvars(required_vars = {
                'DHIS_TOKEN': DHIS_TOKEN,
                'DHIS_URL': DHIS_URL,
                'PARENT_OU': PARENT_OU,
                'OU_LEVEL': OU_LEVEL,
            }
    )

    input_dir = os.path.join(os.getcwd(), 'input')
    os.makedirs(input_dir, exist_ok=True)

    try:
        os.chmod(input_dir, 0o755)
    except PermissionError:
        pass

    logger.info("Fetching Geojson for orgUnit level %s under parent %s", OU_LEVEL, PARENT_OU)

    org_units = get_dhis_geojson(parent_ou = PARENT_OU,
                                 ou_level = OU_LEVEL,
                                 dhis_url = DHIS_URL,
                                 dhis_token = DHIS_TOKEN)

    output_path = os.path.join(input_dir, "orgUnit_poly.geojson")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(org_units, f, ensure_ascii=False)

    logger.info("Saved geojson polygons to %s", output_path)

if __name__ == "__main__":
    fetch_geojson()

