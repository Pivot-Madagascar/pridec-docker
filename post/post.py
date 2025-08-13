import os
from dotenv import load_dotenv
load_dotenv()

import requests
from requests.auth import HTTPBasicAuth
import json

DHIS2_URL = os.getenv("DHIS2_PRIDEC_URL")
API_TOKEN = os.getenv("DHIS2_TOKEN")
DISEASE_CODE = os.getenv("DISEASE_CODE")
dryRun = os.getenv("DRYRUN", "true").lower() == "true"

print("Posting forecast to instance")

if dryRun:
    print("🏁 Running in DRY RUN mode - no changes will be made.")
else:
    print("🚀 Running in normal mode. Data will be imported into instance.")

#this is direct from pridec-gee package
def post_dataValues(base_url, payload, user=None, pwd=None, token=None, dryRun=False):

    """
    Posts dataElement values to a dhis2 instance

    Args:
        base_url (str)           url of dhis2 isntance
        payload (dict)           JSON payload to send in POST
        user (str, optional)     ousername for dhis2 instance
        pwd (str, optional)      password for dhis2 instance
        token (str, optional)    personal access token for dhis2 instance.
                                 Can be provided instead of user and pwd.
        dryRun (boolean)         True: test a dry run of the POST
                                 False: actually post the data
    
    Returns:
        requests.Response: Response object from POST request
    """
    if not token and not (user and pwd):
        raise ValueError("Authentication required: provide either a token or both user and pwd")

    endpoint = (
        "api/dataValueSets"
        f"?dryRun={'true' if dryRun else 'false'}"
        "&dataElementIdScheme=code"
        "&orgUnitIdScheme=uid"
        "&categoryOptionComboIdScheme=code"
        "&idScheme=code"
        "&importStrategy=CREATE_AND_UPDATE"
    )


    url = f"{base_url.rstrip('/')}/{endpoint}"

    # Authentication setup
    headers = {'Authorization': f'ApiToken {token}'} if token else {}
    auth = None if token else HTTPBasicAuth(user, pwd)
    
    #send request
    response = requests.post(url, headers=headers, auth=auth, json=payload)

    # resp.json().get("httpStatus")
    # resp_text = response.json().get("status")
    # resp.json().get("message")
    # resp_text = response.json().get("response")

    return response

print(f"Posting forecast for {DISEASE_CODE} to {DHIS2_URL}")

with open('output/forecast.json', 'r') as file:
    json_payload = json.load(file)

resp = post_dataValues(base_url = DHIS2_URL, payload = json_payload, token = API_TOKEN, dryRun = dryRun)
if resp.ok:
    print(f"✅ Successfully POSTed {DISEASE_CODE}")
else:
    print(f"❌ Failed to POST {DISEASE_CODE} with status code {resp.status_code}")
    print("Response:", resp.text)

