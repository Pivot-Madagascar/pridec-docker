#source .venv/bin/activate

import os
from dotenv import load_dotenv
load_dotenv()

import requests
import json

DHIS2_URL = os.getenv("DHIS2_PRIDEC_URL")
API_TOKEN = os.getenv("TOKEN_DHIS_PRIDEC_MICHELLE")
DISEASE_CODE = os.getenv("DISEASE_CODE")
OU_PARENT = os.getenv("PARENT_OU")
OU_LEVEL = 5 if "CSB" in DISEASE_CODE else 6 #csb (5) for csb-level predictions, otherwise fokontany (6)

print(f"🔍 Fetching geojson for level {OU_LEVEL} units under parent orgUnit {OU_PARENT}")


#function from pridec-gee package
def get_dhis_geojson(PARENT_OU, OU_LEVEL, dhis_url, dhis_user=None, dhis_pwd=None, dhis_token=None):

    """
    GETs geojson of orgUnits from DHIS2 instance. Based on function from pridec-gee package.
    
    Args:
        PARENT_OU (string): id of parent orgUnit
        OU_LEVEL (int): hierarchy level of OrgUnit (6 = fokontany, 5 = csb)
        dhis_url (string): base url of DHIS2 instance
        dhis_user (str, optional) :   username for dhis2 instance
        dhis_pwd (str, optional)  :   password for dhis2 instance
        dhis_token (str, optional):   personal access token for dhis2 instance.
                                 Can be provided instead of user and pwd.

    Returns:
        FeatureCollection: geojson of orgUnits
    """

    if not dhis_token and not (dhis_user and dhis_pwd):
        raise ValueError("Authentication required: provide either a token or both user and pwd")

    # Authentication setup
    headers = {'Authorization': f'ApiToken {dhis_token}'} if dhis_token else {}
    auth = None if dhis_token else HTTPBasicAuth(dhis_user, dhis_pwd)
    geo_url = f"{dhis_url}api/organisationUnits.geojson?parent={PARENT_OU}&level={OU_LEVEL}"

    response = requests.get(geo_url, headers = headers, auth = auth)
    response.raise_for_status()
    geojson = response.json()

    #remove point geometries
    geojson["features"] = [
    feat for feat in geojson["features"]
    if feat.get("geometry", {}).get("type") not in {"Point", "MultiPoint"}
]

    org_units = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": {
                    "orgUnit": feature["id"]
                }
            }
            for feature in geojson["features"]
            if "geometry" in feature and feature["geometry"]
        ]
        }
    return org_units


#fetch and save
org_units = get_dhis_geojson(PARENT_OU=OU_PARENT, OU_LEVEL=OU_LEVEL, dhis_token=API_TOKEN, dhis_url=DHIS2_URL)
with open("input/orgUnit_poly.geojson", "w", encoding="utf‑8") as f:
    json.dump(org_units, f, ensure_ascii=False)

print(f"✅ Saved geojson polygons to input/orgUnit_poly.geojson")