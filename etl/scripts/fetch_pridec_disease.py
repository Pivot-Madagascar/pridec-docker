from config import DHIS_TOKEN, DHIS_URL, PARENT_OU, OU_LEVEL, DISEASE_CODE, setup_logging, check_envvars
from pivot_dhis_tools import pridec_fetch_disease
import os
import json

import logging

setup_logging()

logger = logging.getLogger("import_pivot_COM")

check_envvars(required_vars = {
            'DHIS_TOKEN': DHIS_TOKEN,
            'DHIS_URL': DHIS_URL,
            'PARENT_OU': PARENT_OU,
            'OU_LEVEL': OU_LEVEL,
            'DISEASE_CODE': DISEASE_CODE
        }
)

logger.info("Fetching disease data %s from %s", DISEASE_CODE, DHIS_URL)

if not os.path.isdir('input'):
    raise NotADirectoryError("Directory 'input' not found.")

data_out = pridec_fetch_disease(dhis_url = DHIS_URL, ou_level = 5, 
                     ou_parent =  PARENT_OU,
                     disease_code = DISEASE_CODE,
                     token=DHIS_TOKEN, past_years = 6)

with open("input/disease_data.json", "w") as f:
    json.dump({"dataValues": data_out}, f, indent=2)

logger.info("Saved %s to input/disease_data.json", DISEASE_CODE)