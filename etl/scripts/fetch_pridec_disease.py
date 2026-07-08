from pivot_dhis_tools import pridec_fetch_disease
import os
import json
import logging

def print_help():
    print(f"""
Task: fetch_pridec_disease

Usage:
-   Downloads PRIDE-C disease data from DHIS2 instance and saves into `input` folder. 

Notes:
-   Disease data will be downloaded for the orgUnit level specified in .env via OU_LEVEL.
    Fokontany = 6. CSB = 5.
-   The dataElement with code corresponding to env var DISEASE_CODE will be downloaded.
    Options: 
""")

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(add_help=False) # disable default help
    parser.add_argument("--help", "-h", action="store_true")
    return parser.parse_args()

def fetch_disease():
    from etl.scripts.config import DHIS_TOKEN, DHIS_URL, PARENT_OU, OU_LEVEL, DISEASE_CODE, setup_logging, check_envvars

    setup_logging()

    logger = logging.getLogger("fetch_disease")

    check_envvars(required_vars = {
                'DHIS_TOKEN': DHIS_TOKEN,
                'DHIS_URL': DHIS_URL,
                'PARENT_OU': PARENT_OU,
                'OU_LEVEL': OU_LEVEL,
                'DISEASE_CODE': DISEASE_CODE
            }
    )

    #TO DO: Update to get OU automatically based on disease code

    logger.info("Fetching disease data %s from %s", DISEASE_CODE, DHIS_URL)

    input_dir = os.path.join(os.getcwd(), 'input')
    os.makedirs(input_dir, exist_ok=True)

    try:
        os.chmod(input_dir, 0o755)
    except PermissionError:
        pass

    data_out = pridec_fetch_disease(dhis_url = DHIS_URL, ou_level = OU_LEVEL,
                         ou_parent =  PARENT_OU,
                         disease_code = DISEASE_CODE,
                         token=DHIS_TOKEN, past_years = 6)

    output_path = os.path.join(input_dir, "disease_data.json")
    with open(output_path, "w") as f:
        json.dump({"dataValues": data_out}, f, indent=2)

    logger.info("Saved %s to input/disease_data.json", DISEASE_CODE)

if __name__ == "__main__":
    args = parse_args()
    if args.help:
        print_help()
        exit(0)
    fetch_disease()