# source .venv/bin/activate

import requests
from requests.auth import HTTPBasicAuth
import json
import os
import pandas as pd

from dotenv import load_dotenv
load_dotenv(override=True)
from utils import GET_disease, check_dhis_value, post_dataValues, create_period

DHIS2_URL = os.getenv("DHIS2_PRIDEC_URL")
DHIS2_TOKEN = os.getenv("DHIS2_TOKEN")
PIVOT_URL = os.environ.get("PIVOT_URL")
PIVOT_TOKEN = os.environ.get("PIVOT_TOKEN")
dryRun = os.getenv("DRYRUN", "true").lower() == "true"

print("Importing CSB Case Data.")

if dryRun:
    print("🚀 Running in DRY RUN mode — no changes will be made.")
else:
    print("✅ Running in normal mode. Data will be imported into instance.")

period_list = create_period(n_months = 8)



# ------------------CSB Data --------------------
csb_ids = [
    "D9UWDj19ljP", "U1YeJp3NDNV", "DDR2w1c1GyE", "uWoBok9YyvB",
    "O1wNJut8eci", "FGM6Ric1YnC", "r4U7PhBKR7S", "RRe6ic0AU1Z",
    "okDqhh9n4yT", "z6kDxHwInUT", "h0z1bKoHDrU", "Pi2y9HFBDRj",
    "pczrAub8lnt", "YCvVB1VwWi0", "hXuxS0MOq3b", "mBZLeZ7Irx6",
    "WCqkkkKNJEi", "EE6WwIMgQ0F", "M38BJM8ju1A", "ZPvH8UsgwYv",
    "QHPyq70qulM"
]

csb_org_query = f"ou:{';'.join(csb_ids)}"

##  -------------------Malaria --------
# wuwA8DT9h7c (Numerator) - RDT + at CSB for 2-11 months 
# PVu7GgpuJNV (Numerator) - RDT + at CSB for 1-5 years

palu_1y = GET_disease(pivot_url = PIVOT_URL,
                      pivot_token = PIVOT_TOKEN,
                      dx_query =  "dx:wuwA8DT9h7c",
                      pe_query = period_list,
                      ou_query = csb_org_query,
                      includeNumDen=True)
palu_5y = GET_disease(pivot_url = PIVOT_URL,
                      pivot_token = PIVOT_TOKEN,
                      dx_query =  "dx:PVu7GgpuJNV",
                      pe_query = period_list,
                      ou_query = csb_org_query,
                      includeNumDen=True)
palu_all = (
    pd.concat([palu_1y, palu_5y], ignore_index=True)
    .rename(columns={
        'ou': 'orgUnit',
        'pe' : 'period'})
    .assign(numerator = lambda x: pd.to_numeric(x['numerator'], errors = 'coerce', downcast='integer'))
    .groupby(['period', 'orgUnit'], as_index=False)
    .agg(value=('numerator', 'sum'))
    .assign(dataElement = 'pridec_historic_CSBMalaria')
    .assign(categoryOptioncombo = 'pridec_COC_u5')
)

check_dhis_value(palu_all)

CSBMalaria_json = {
    "dataValues": palu_all.to_dict(orient="records")
}

print(f"Importing pridec_historic_CSBMalaria")

resp = post_dataValues(base_url = DHIS2_URL, payload = CSBMalaria_json, token = DHIS2_TOKEN, dryRun = dryRun)
if resp.ok:
    print(f"✅ Successfully imported pridec_historic_CSBMalaria")
else:
    print(f"❌ Failed to import pridec_historic_CSBMalaria with status code {resp.status_code}")
    print("Response:", resp.text)

## ----------------CSB IRA ---------------------
# IRA data is in two dataElements that both have a lot of comboCategories

ira_co = "co:HIsTqXVmDdV;TJlRzxBqiqG;ncBrGeQ9w2g;YAxDQLsxeT0;fEAWzG9dj98;yprE1T7gBUw;lwrX7wJqjhW;DSaVQguA6v6"

ira_csb = GET_disease(pivot_url = PIVOT_URL,
                      pivot_token = PIVOT_TOKEN,
                      dx_query =  "dx:eHrqdPNZW6m;E4KUPwZuLrG",
                      pe_query = period_list,
                      ou_query = csb_org_query,
                      co_query = ira_co,
                      includeNumDen=False)

ira_all = (
    ira_csb
    .rename(columns={
        'ou': 'orgUnit',
        'pe' : 'period'})
    .assign(value = lambda x: pd.to_numeric(x['value'], errors = 'coerce', downcast='integer'))
    .groupby(['period', 'orgUnit'], as_index=False)
    .agg(value=('value', 'sum'))
    .assign(dataElement = 'pridec_historic_CSBRespinf')
    .assign(categoryOptioncombo = 'pridec_COC_u5')
)

check_dhis_value(ira_all)


CSBRespinf_json = {
    "dataValues": ira_all.to_dict(orient="records")
}

print(f"Importing pridec_historic_CSBRespinf")

resp = post_dataValues(base_url = DHIS2_URL, payload = CSBRespinf_json, token = DHIS2_TOKEN, dryRun = dryRun)
if resp.ok:
    print(f"✅ Successfully imported pridec_historic_CSBRespinf")
else:
    print(f"❌ Failed to import pridec_historic_CSBRespinf with status code {resp.status_code}")
    print("Response:", resp.text)

## ------------------------ CSB Diarrhea ------------------------------
# uses same co as ira

diar_csb = GET_disease(pivot_url = PIVOT_URL,
                      pivot_token = PIVOT_TOKEN,
                      dx_query =   "dx:uw5yUgtSYfQ;kvoIFhX5RMA;NG2mlKX2D6C",
                      pe_query = period_list,
                      ou_query = csb_org_query,
                      co_query = ira_co,
                      includeNumDen=False)

diar_all = (
    diar_csb
    .rename(columns={
        'ou': 'orgUnit',
        'pe' : 'period'})
    .assign(value = lambda x: pd.to_numeric(x['value'], errors = 'coerce', downcast='integer'))
    .groupby(['period', 'orgUnit'], as_index=False)
    .agg(value=('value', 'sum'))
    .assign(dataElement = 'pridec_historic_CSBDiarrhea')
    .assign(categoryOptioncombo = 'pridec_COC_u5')
)

check_dhis_value(diar_all)


CSBDiarrhea_json = {
    "dataValues": diar_all.to_dict(orient="records")
}

print(f"Importing pridec_historic_CSBDiarrhea")

resp = post_dataValues(base_url = DHIS2_URL, payload = CSBDiarrhea_json, token = DHIS2_TOKEN, dryRun = dryRun)
if resp.ok:
    print(f"✅ Successfully imported pridec_historic_CSBDiarrhea")
else:
    print(f"❌ Failed to import pridec_historic_CSBDiarrhea with status code {resp.status_code}")
    print("Response:", resp.text)
