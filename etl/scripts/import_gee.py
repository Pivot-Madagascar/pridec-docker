from config import DHIS_TOKEN, DHIS_URL, PARENT_OU, GEE_SERVICE_ACCOUNT, GEE_VARIABLES, dryRun, setup_logging, check_envvars
import json
import ee
import os

import logging

setup_logging()
logger = logging.getLogger("import_gee")

from importlib.resources import files

from pridec_gee import import_pridec_climate
from pridec_gee import calc_date_range

check_envvars(required_vars = {
            'DHIS_TOKEN': DHIS_TOKEN,
            'DHIS_URL': DHIS_URL,
            'PARENT_OU': PARENT_OU,
            'GEE_SERVICE_ACCOUNT': GEE_SERVICE_ACCOUNT,
            'GEE_VARIABLES' : GEE_VARIABLES
        }
)

# configs and env vars
if not os.path.isfile('.gee-private-key.json'):
    raise FileNotFoundError("'.gee-private-key.json' not found.")

credentials = ee.ServiceAccountCredentials(GEE_SERVICE_ACCOUNT, ".gee-private-key.json")
ee.Initialize(credentials)

ou_level = 6 #fokontany, hardcoded

#load rice fields 
geojson_path = files("pridec_gee").joinpath("data/pivot_major_rice.geojson")

with open(geojson_path, 'r') as f:
    rice_json = json.load(f)
rice_fields = ee.FeatureCollection(rice_json)

date_range = calc_date_range(start_months_ago=3,
                             end_on_last_day=True)

#will output to console 
import_pridec_climate(dhis_url=DHIS_URL,  dhis_token=DHIS_TOKEN, date_range=date_range, 
                      orgUnit=None, parent_ou=PARENT_OU, ou_level=ou_level, #download from instance
                      variables= GEE_VARIABLES,
                      rice_features=rice_fields, dryRun=dryRun)
