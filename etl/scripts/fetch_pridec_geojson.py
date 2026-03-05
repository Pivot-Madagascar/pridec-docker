from config import DHIS_TOKEN, DHIS_URL, OU_LEVEL, PARENT_OU, setup_logging
from requests.auth import HTTPBasicAuth
import logging
import json

from pridec_gee import get_dhis_geojson

setup_logging()

logger = logging.getLogger("fetch_pridec_geojson")

logger.info("Fetching Geojson for orgUnit level %s under parent %s", OU_LEVEL, PARENT_OU)

org_units = get_dhis_geojson(parent_ou = PARENT_OU,
                             ou_level = OU_LEVEL,
                             dhis_url = DHIS_URL,
                             dhis_token = DHIS_TOKEN)

with open("input/orgUnit_poly.geojson", "w", encoding="utf‑8") as f:
    json.dump(org_units, f, ensure_ascii=False)

logger.info("Saved geojson polygons to input/orgUnit_poly.geojson")

