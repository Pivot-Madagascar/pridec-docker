from config import DHIS_TOKEN, DHIS_URL, PARENT_OU, OU_LEVEL, setup_logging, check_envvars
from pivot_dhis_tools import pridec_fetch_climate
import os
import json

import logging

setup_logging()

logger = logging.getLogger("import_pivot_COM")

logger.info("Fetching PRIDEC Climate data from %s", DHIS_URL)

if not os.path.isdir('input'):
    raise NotADirectoryError("Directory 'input' not found.")

#check envvars
check_envvars(required_vars={
    'DHIS_TOKEN': DHIS_TOKEN,
    'DHIS_URL': DHIS_URL,
    'PARENT_OU': PARENT_OU,
    'OU_LEVEL': OU_LEVEL,
})

data_out = pridec_fetch_climate(dhis_url = DHIS_URL, ou_level = OU_LEVEL, 
                     ou_parent =  PARENT_OU,
                     token=DHIS_TOKEN, past_years = 8)

with open("input/climate_data.json", "w") as f:
    json.dump({"dataValues": data_out}, f, indent=2)

logger.info("Saved all PRIDE-C climate variables to input/climate_data.json")

