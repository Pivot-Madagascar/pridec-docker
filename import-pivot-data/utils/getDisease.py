import requests
from requests.auth import HTTPBasicAuth
import json
import os
import pandas as pd

from dotenv import load_dotenv
load_dotenv(override=True)

#for debugging
pivot_url = os.environ.get("PIVOT_URL")
pivot_token = os.environ.get("PIVOT_TOKEN")

dx_query = "dx:wuwA8DT9h7c"
ou_query = "ou:LEVEL-5;VtP4BdCeXIo"
pe_query = "pe:202401;202402"
co_query = None
includeNumDen = True

def GET_disease(pivot_url, pivot_token, dx_query, ou_query, pe_query, co_query=None, includeNumDen=False):
    """
    GET dataValues for query of dataElement, orgunits, and periods

    Args:
        pivot_url (string)          base url of DHIS for APIs
        pivot_token (string)        personal access token for DHIS instance
        dx_query (string)           id of dataElement or Indicator to download. can supply multiple if seperated by ;. Must starts with `dx:`
        ou_query (string)           list of orgUnit ids to download. Can also be a DHIS2 call to a certain level such as ["ou:LEVEL-z7UyvgYEMRa;VtP4BdCeXIo"]
                                    Must start with `ou:`
        pe_query (string)           list of periods in YYYYMM to download, seperated by ;. Must start with `pe:`
        co_query (string)           list of category options to download, seperated by;. Must start with `co:`. Default = None
        includeNumDen (boolean)     whether to download the numerator and denominator of indicators. Default = False
    Returns:
        pandas Data.Frame of data with columns ...
    """
    
    params = {
        "dimension": [q for q in [dx_query, ou_query, pe_query, co_query] if q is not None],
        "includeNumDen": includeNumDen
    }

    api_url = f"{pivot_url.rstrip('/')}/api/analytics.json?"
    headers = {"Authorization": f"ApiToken {pivot_token}"}

    # print(requests.Request("GET", api_url, params=params).prepare().url)

    response = requests.get(api_url, params=params, headers=headers)
    response.raise_for_status() 

    data_df = json_to_dataframe(response.json())

    return data_df

def json_to_dataframe(data):
    headers = [h["name"] for h in data["headers"]]  
    df = pd.DataFrame(data["rows"], columns=headers)
    return df