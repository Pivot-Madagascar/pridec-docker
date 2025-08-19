import os
from dotenv import load_dotenv
load_dotenv()

import requests
from requests.auth import HTTPBasicAuth

print("Rebuilding Analytics Tables")

DHIS2_URL = os.getenv("DHIS2_PRIDEC_URL")
API_TOKEN = os.getenv("DHIS2_TOKEN")
DISEASE_CODE = os.getenv("DISEASE_CODE")
dryRun = os.getenv("DRYRUN", "true").lower() == "true"

if dryRun:
    print("🏁 Running in DRY RUN mode - will not update Analytics Tables.")
    quit()
else:
    print("🚀 Running in normal mode. Analytics Tables will be run.")


#from pridec-gee package
def launch_analytics(base_url, user=None, pwd=None, token=None, dryRun=False):
    """
    Launches Analytics Tables on a dhis2 instance

    Args:
        base_url (str)           url of dhis2 isntance
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

    endpoint = "api/33/resourceTables/analytics"


    url = f"{base_url.rstrip('/')}/{endpoint}"

    # Authentication setup
    headers = {'Authorization': f'ApiToken {token}'} if token else {}
    auth = None if token else HTTPBasicAuth(user, pwd)
    
    #send request
    response = requests.post(url, headers=headers, auth=auth)

    # resp.json().get("httpStatus")
    # resp.json().get("status")
    # resp.json().get("message")
    # resp_text = response.json().get("response") #for debugging

    return response

# ----------- Rebuild Analytics Tables ----------------------#



resp = launch_analytics(base_url=DHIS2_URL, token=API_TOKEN)
if resp.ok:
    analytics_endpoint = resp.json().get("response")['relativeNotifierEndpoint']
    print(f"✅ Successfully launched export of analytics table.")
    print(f"View status at {DHIS2_URL.rstrip('/')}{analytics_endpoint}")
else:
    print(f"❌ Failed to export analytics table.")
    print("Response:", resp.text)