import os
from dotenv import load_dotenv
load_dotenv()

import requests
from requests.auth import HTTPBasicAuth
import json

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