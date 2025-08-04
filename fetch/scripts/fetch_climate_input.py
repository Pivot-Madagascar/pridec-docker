#source .venv/bin/activate

import os
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests
import json

DHIS2_URL = os.getenv("DHIS2_PRIDEC_URL")
API_TOKEN = os.getenv("DHIS2_TOKEN")
DISEASE_CODE = os.getenv("DISEASE_CODE")
OU_LEVEL = 5 if "CSB" in DISEASE_CODE else 6 #csb (5) for csb-level predictions, otherwise fokontany (6)
OU_PARENT = os.getenv("PARENT_OU")
ORGUNITS = f"LEVEL-{OU_LEVEL};{OU_PARENT}"

headers = {"Authorization": f"ApiToken {API_TOKEN}"}

# --- Create range of dates ----------- #
#should get data from past 10 years (121)
def generate_periods(start_offset=-121, end_offset=-1):
    periods = []
    current = datetime.today().replace(day=1) + relativedelta(months=start_offset)
    end = datetime.today().replace(day=1) + relativedelta(months=end_offset)
    while current <= end:
        periods.append(current.strftime('%Y%m'))
        current += relativedelta(months=1)
    return ";".join(periods)

periods = generate_periods()

#--- Identify instance-specific climate dataelement IDs from PRIDE-C -----#

de_lookup_url = (
    f"{DHIS2_URL}/api/dataElements"
    f"?filter=code:like:pridec_climate"
    f"&fields=id,code,displayName"
    f"&paging=false"
)

resp = requests.get(de_lookup_url, headers=headers)
resp.raise_for_status()

data_elements = resp.json()["dataElements"]

if not data_elements:
    raise ValueError("No dataElements found with code prefix 'pridec_climate'")

print(f"📦 Found {len(data_elements)} dataElements with code starting 'pridec_climate'")

#---- Fetch from instance and save --------------#

flattened = []

for element in data_elements:
    de_uid = element["id"]
    de_code = element["code"]

    analytics_url = (
        f"{DHIS2_URL}api/analytics.json"
        f"?dimension=dx:{de_uid}"
        f"&dimension=ou:{ORGUNITS}"
        f"&dimension=pe:{periods}"
        f"&includeNumDen=false"
    )

    print(f"🔍 Fetching data for {de_code}...")

    resp = requests.get(analytics_url, headers=headers)
    resp.raise_for_status()

    data = resp.json()

    headers_map = {h['name']: i for i, h in enumerate(data.get("headers", []))}

    for row in data.get("rows", []):
        flattened.append({
            "orgUnit": row[headers_map["ou"]],
            "period": row[headers_map["pe"]],
            "dataElement": de_code,
            "value": float(row[headers_map["value"]])
        })

# --- Save combined result to JSON ---

# print("First 5 data values:\n", json.dumps(flattened[:5], indent=2))

with open("input/climate_data.json", "w") as f:
    json.dump({"dataValues": flattened}, f, indent=2)

print("✅ Saved all climate analytics to input/climate_data.json")
