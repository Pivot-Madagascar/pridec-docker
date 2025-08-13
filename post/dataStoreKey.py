import os
from dotenv import load_dotenv
load_dotenv()

import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime

print("Updating dataStore/pridec/pridec_update")

DHIS2_URL = os.getenv("DHIS2_PRIDEC_URL")
API_TOKEN = os.getenv("DHIS2_TOKEN")
dryRun = os.getenv("DRYRUN", "true").lower() == "true"

if dryRun:
    print("🏁 Running in DRY RUN mode - will not update dataStore key.")
    quit()
else:
    print("🚀 Running in normal mode. Updating dataStore key.")

endpoint = "/api/33/dataStore/pridec/pridec_update"

url = f"{DHIS2_URL.rstrip('/')}/{endpoint}"

# Authentication setup
headers = {'Authorization': f'ApiToken {API_TOKEN}'}

this_key = {
    "pridec_update": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
}

json_key = json.dumps(this_key)

resp = requests.put(
    url,
    headers = headers,
    json = json_key
)

if resp.ok:
    print(f"✅ Successfully updated dataStore key to {this_key['pridec_update']}")
else:
    print(f"❌ Failed to update dataStore key with status code {resp.status_code}")
    print("Response:", resp.text)
