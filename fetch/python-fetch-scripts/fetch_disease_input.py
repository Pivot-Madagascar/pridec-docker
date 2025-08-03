#source .venv/bin/activate

import os
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests
import json

DHIS2_URL = os.getenv("DHIS2_PRIDEC_URL")
API_TOKEN = os.getenv("TOKEN_DHIS_PRIDEC_MICHELLE")
DISEASE_CODE = os.getenv("DISEASE_CODE")
OU_LEVEL = 5 if "CSB" in DISEASE_CODE else 6 #csb (5) for csb-level predictions, otherwise fokontany (6)
OU_PARENT = os.getenv("PARENT_OU")
ORGUNITS = f"LEVEL-{OU_LEVEL};{OU_PARENT}"

headers = {"Authorization": f"ApiToken {API_TOKEN}"}

# --- Create range of dates ----------- #
#should get data from past 6 years (73)
def generate_periods(start_offset=-73, end_offset=-1):
    periods = []
    current = datetime.today().replace(day=1) + relativedelta(months=start_offset)
    end = datetime.today().replace(day=1) + relativedelta(months=end_offset)
    while current <= end:
        periods.append(current.strftime('%Y%m'))
        current += relativedelta(months=1)
    return ";".join(periods)

periods = generate_periods()

# ----- Identify instance-specific dataElemetn IDs from PRIDE-C -----------#
de_lookup_url = (
    f"{DHIS2_URL}/api/dataElements"
    f"?filter=code:like:{DISEASE_CODE}"
    f"&fields=id,code,displayName"
    f"&paging=false"
)

resp = requests.get(de_lookup_url, headers=headers)
resp.raise_for_status()

DISEASE_UID = resp.json()["dataElements"]
if not DISEASE_UID:
    raise ValueError(f"No dataElements found with code {DISEASE_CODE}")

#-------------- Fetch from instance and save ------------#
flattened = []

analytics_url = (
        f"{DHIS2_URL}api/analytics.json"
        f"?dimension=dx:{DISEASE_UID[0]["id"]}"
        f"&dimension=ou:{ORGUNITS}"
        f"&dimension=pe:{periods}"
        f"&includeNumDen=false"
)

print(f"🔍 Fetching data for {DISEASE_CODE} ...")

resp = requests.get(analytics_url, headers=headers)
resp.raise_for_status()
data = resp.json()

 # Get index positions of columns
headers_map = {h['name']: i for i, h in enumerate(data.get("headers", []))}

for row in data.get("rows", []):
    flattened.append({
        "orgUnit": row[headers_map["ou"]],
        "period": row[headers_map["pe"]],
        "dataElement": DISEASE_CODE,
        "value": float(row[headers_map["value"]])
     })
    
# --- Save combined result to JSON ---

# print("First 5 data values:\n", json.dumps(flattened[:5], indent=2))

with open("input/disease_data.json", "w") as f:
    json.dump({"dataValues": flattened}, f, indent=2)

print(f"✅ Saved historical data for {DISEASE_CODE} to input/disease_data.json")