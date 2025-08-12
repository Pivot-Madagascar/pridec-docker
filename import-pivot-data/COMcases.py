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

print("Importing COM Case Data")

if dryRun:
    print("🚀 Running in DRY RUN mode — no changes will be made.")
else:
    print("✅ Running in normal mode. Data will be imported into instance.")

period_list = create_period(n_months = 8)

com_ids = [
    "nkoqILeLIGJ", "NGjuCieFofW", "NGk42ableWs", "NgNK7cFJDLR", "ngOUK2x3rO8", "nGswNcrtBCW", "NGuHJF8vef8", "NGxXvp7qi48",
    "nh1SDW0DuQP", "NH6km4XsRdx", "NhBFAojLAnq", "NhcIarFZ0gg", "nHeDldiT3lB", "NhgHicA7zmx", "NHGlRwg0Qwu", "nhp8hOvQUT3",
    "NhPMW9k508q", "nhR0Pat5DlD", "NHsAEr2hrhx", "NHTwonuDKC6", "nHTZ72jAFvv", "NHvhM6egCml", "NHVkAeLFPcK", "ni2fhsEBQV4",
    "Ni6HLgy72nt", "nI8ROa8oOxH", "niA2fAJNCjN", "nIcna9odW5i", "NIF2yn3SFhU", "NiGaS2wQ7nC", "nIhczINg82d", "niiqdtu9lFU",
    "NioaQKw6eR8", "NiOIIht8nBW", "NiPVq9fdj9I", "niPWWDnI4AE", "Niqsy6XdJfM", "niqxHXfJaZg", "nit1VMYMSEc", "nIU59blKoSz",
    "nJ41cDAbDTK", "njF5rCZeEin", "NjFmT8vGYte", "nJg2gFtkEQG", "NjgEEmvRRTt", "njIuCDYoiFv", "nkIbspPvmRh", "nKiccllE1Gt",
    "NKnlmpvCHID", "NkUoPHdmiA2", "NKVKLTSXOa9", "nKX9oIy5HTw", "nKzUk8iUYao", "Nl3gjVEOoCS", "nL4inf71e6v", "NlA2gFHEn2e",
    "NLbaZ2vV52C", "nLcJCGOmAq5", "Nle2yV3LLqH", "NlgNaSRnFOb", "NLhVCk2cWFQ", "nLJ2df5ihXt", "Nlj6ztotjaY", "nll5Vf4HO0u",
    "nlLJxsMVKbi", "nlyV8TTcLAC", "nm0fEIqvkKG", "nm0HDq47aqP", "nObSjXaMtmC", "NocwbwPY49A", "NoDz1A2X03y", "NOf5U0kPmmS",
    "noGSitwu1YV", "NojOuDYO6d9", "NOKJwSSC9yV", "nongBlHhnBk", "NoTbIakXnYE", "noTUS4NpOt9", "NOUicYmzdkM", "nOvkLuoAvaE",
    "NoYX2eHiThV", "Np9zQuuUkT0", "npDsoxdC4tm", "nPErooJK6FG", "NPG9aF3lhTC", "nPjsBwjNwN5", "nPKeJthEM73", "NpOSpQvGHoL",
    "NPoWFLdHHLc", "nPUb0c5EcMk", "nPX6RxV9I6v"
]

com_org_query = f"ou:{';'.join(com_ids)}"

##  -------------------Total Consultations ---------------
# This is used to identify missing data vs. zeroes
# lq38tLcfEi7 - RMA_COM_PCIMEc Nombre d'enfants reçu au site 

com_get = GET_disease(pivot_url = PIVOT_URL,
                      pivot_token = PIVOT_TOKEN,
                      dx_query =  "dx:lq38tLcfEi7",
                      pe_query = period_list,
                      ou_query = com_org_query,
                      includeNumDen=False)
com_all = (
    com_get
    .rename(columns={
        'ou': 'orgUnit',
        'pe' : 'period',
        'value' : 'chw_all'})
    .assign(chw_all = lambda x: pd.to_numeric(x['chw_all'], errors = 'coerce', downcast='integer'))
)

full_grid = (
    pd.DataFrame({'orgUnit' : com_all['orgUnit'].unique()})
    .merge(pd.DataFrame({'period' : com_all['period'].unique()}), how = 'cross')
    .merge(com_all, on = ['orgUnit', 'period'], how="outer")
)

#-------------COM Malaria --------------------------------
# vduU8d1GZbW : RMA_COM_PCIMEc Nombre de cas de fièvre testés avec TDR positif 

print("Getting pridec_historic_COMMalaria")

mal_get = GET_disease(pivot_url = PIVOT_URL,
                      pivot_token = PIVOT_TOKEN,
                      dx_query =  "dx:vduU8d1GZbW",
                      pe_query = period_list,
                      ou_query = com_org_query,
                      includeNumDen=False)

mal_all = (
    mal_get
    .rename(columns={
        'ou': 'orgUnit',
        'pe' : 'period'})
    .assign(value= lambda x: pd.to_numeric(x['value'], errors = 'coerce', downcast='integer'))
    .merge(full_grid, on = ['orgUnit', 'period'], how="outer")
    .assign(value=lambda x: x.apply(lambda row: 0 if pd.notna(row['chw_all']) and pd.isna(row['value']) else row['value'], axis=1))
    .loc[:, ['period', 'orgUnit', 'value']]
    .assign(dataElement = 'pridec_historic_COMMalaria')
    .assign(categoryOptioncombo = 'pridec_COC_u5')
    .dropna(subset=['value'])
    .assign(value= lambda x: pd.to_numeric(x['value'], errors = 'coerce', downcast='integer'))
)

check_dhis_value(mal_all)

COMMalaria_json = {
    "dataValues": mal_all.to_dict(orient="records")
}

print("Importing pridec_historic_COMMalaria")

resp = post_dataValues(base_url = DHIS2_URL, payload = COMMalaria_json, token = DHIS2_TOKEN, dryRun = dryRun)
if resp.ok:
    print(f"✅ Successfully imported pridec_historic_COMMalaria")
else:
    print(f"❌ Failed to import pridec_historic_COMMalaria with status code {resp.status_code}")
    print("Response:", resp.text)

## ----------------COM IRA ---------------------
#' hJ5pa6wO4nJ : RMA_COM_PCIMEc Nombre d’enfants présentant de pneumonie 
#' CmDXCmmywrj : RMA_COM_PCIMEc Nombre d’enfants présentant de  toux ou rhume

print("Getting pridec_historic_COMRespinf")

ira_get = GET_disease(pivot_url = PIVOT_URL,
                      pivot_token = PIVOT_TOKEN,
                      dx_query =  "dx:hJ5pa6wO4nJ;CmDXCmmywrj",
                      pe_query = period_list,
                      ou_query = com_org_query,
                      includeNumDen=False)

ira_all = (
    ira_get
    .rename(columns={
        'ou': 'orgUnit',
        'pe' : 'period'})
    .assign(value= lambda x: pd.to_numeric(x['value'], errors = 'coerce', downcast='integer'))
    .groupby(['period', 'orgUnit'], as_index=False)
    .agg(value=('value', 'sum'))
    .merge(full_grid, on = ['orgUnit', 'period'], how="outer")
    .assign(value=lambda x: x.apply(lambda row: 0 if pd.notna(row['chw_all']) and pd.isna(row['value']) else row['value'], axis=1))
    .loc[:, ['period', 'orgUnit', 'value']]
    .assign(dataElement = 'pridec_historic_COMRespinf')
    .assign(categoryOptioncombo = 'pridec_COC_u5')
    .dropna(subset=['value'])
    .assign(value= lambda x: pd.to_numeric(x['value'], errors = 'coerce', downcast='integer'))
)

check_dhis_value(ira_all)

COMRespinf_json = {
    "dataValues": ira_all.to_dict(orient="records")
}

print("Importing pridec_historic_COMRespinf")

resp = post_dataValues(base_url = DHIS2_URL, payload = COMRespinf_json, token = DHIS2_TOKEN, dryRun = dryRun)
if resp.ok:
    print(f"✅ Successfully imported pridec_historic_COMRespinf")
else:
    print(f"❌ Failed to import pridec_historic_COMRespinf with status code {resp.status_code}")
    print("Response:", resp.text)

# -------------------- COM Diarrhea -------------------

#' DjsQEzPDAoN : RMA_COM_PCIMEc Nombre d’enfants présentant de diarrhée avec signes de danger
#' f4hrhsiz49l : RMA_COM_PCIMEc Nombre d’enfants présentant de diarrhée simple

print("Getting pridec_historic_COMDiarrhea")

diar_get = GET_disease(pivot_url = PIVOT_URL,
                      pivot_token = PIVOT_TOKEN,
                      dx_query =  "dx:DjsQEzPDAoN;f4hrhsiz49l",
                      pe_query = period_list,
                      ou_query = com_org_query,
                      includeNumDen=False)

diar_all = (
    diar_get
    .rename(columns={
        'ou': 'orgUnit',
        'pe' : 'period'})
    .assign(value= lambda x: pd.to_numeric(x['value'], errors = 'coerce', downcast='integer'))
    .groupby(['period', 'orgUnit'], as_index=False)
    .agg(value=('value', 'sum'))
    .merge(full_grid, on = ['orgUnit', 'period'], how="outer")
    .assign(value=lambda x: x.apply(lambda row: 0 if pd.notna(row['chw_all']) and pd.isna(row['value']) else row['value'], axis=1))
    .loc[:, ['period', 'orgUnit', 'value']]
    .assign(dataElement = 'pridec_historic_COMDiarrhea')
    .assign(categoryOptioncombo = 'pridec_COC_u5')
    .dropna(subset=['value'])
    .assign(value= lambda x: pd.to_numeric(x['value'], errors = 'coerce', downcast='integer'))
)

check_dhis_value(diar_all)

COMDiarrhea_json = {
    "dataValues": diar_all.to_dict(orient="records")
}

print("Importing pridec_historic_COMDiarrhea")

resp = post_dataValues(base_url = DHIS2_URL, payload = COMDiarrhea_json, token = DHIS2_TOKEN, dryRun = dryRun)
if resp.ok:
    print(f"✅ Successfully imported pridec_historic_COMDiarrhea")
else:
    print(f"❌ Failed to import pridec_historic_COMDiarrhea with status code {resp.status_code}")
    print("Response:", resp.text)
