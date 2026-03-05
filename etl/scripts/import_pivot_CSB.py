from config import DHIS_TOKEN, DHIS_URL, PIVOT_URL, PIVOT_TOKEN, dryRun, setup_logging, check_envvars
from requests.auth import HTTPBasicAuth
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import logging
#update to pivot_dhis_tools package
# from utils import GET_disease, create_period_range, post_dataValues, check_dhis_value
from pivot_dhis_tools import get_dataElements, create_period_range, check_dhis_value, post_dataElements


setup_logging()
logger = logging.getLogger("import_pivot_CSB")

check_envvars(required_vars = {
            'DHIS_TOKEN': DHIS_TOKEN,
            'DHIS_URL': DHIS_URL,
            'PIVOT_TOKEN': PIVOT_TOKEN,
            'PIVOT_URL': PIVOT_URL,
        }
)

logger.info("Importing CSB Case Data from %s into %s", PIVOT_URL, DHIS_URL)

if dryRun:
    logger.info("DRY RUN — no changes will be made")
else:
    logger.info("NORMAL RUN - data will be imported into instance")

period_list = create_period_range(start = (date.today()-relativedelta(months=8)))

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

palu_1y = get_dataElements(dhis_url = PIVOT_URL,
                      token = PIVOT_TOKEN,
                      dx_query =  "dx:wuwA8DT9h7c",
                      pe_query = period_list,
                      ou_query = csb_org_query,
                      includeNumDen=True)
palu_5y = get_dataElements(dhis_url = PIVOT_URL,
                      token = PIVOT_TOKEN,
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

logger.info("pridec_historic_CSBMalaria has the following characteristics: %s", check_dhis_value(palu_all))

CSBMalaria_json = {
    "dataValues": palu_all.to_dict(orient="records")
}

logger.info(f"Importing pridec_historic_CSBMalaria into PRIDE-C instance with dryRun = %s", dryRun)

resp = post_dataElements(dhis_url = DHIS_URL, payload = CSBMalaria_json, token = DHIS_TOKEN, dryRun = dryRun)
if resp.ok:
    logger.info("Imported pridec_historic_CSBMalaria")
    logger.debug("Response: %s", resp.text)
else:
    logger.error("Failed to import pridec_historic_CSBMalaria with status code %s", resp.status_code)
    logger.error("Response: %s", resp.text)

## ----------------CSB IRA ---------------------
# IRA data is in two dataElements that both have a lot of comboCategories

ira_co = "co:HIsTqXVmDdV;TJlRzxBqiqG;ncBrGeQ9w2g;YAxDQLsxeT0;fEAWzG9dj98;yprE1T7gBUw;lwrX7wJqjhW;DSaVQguA6v6"

ira_csb = get_dataElements(dhis_url = PIVOT_URL,
                      token = PIVOT_TOKEN,
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

logger.info("pridec_historic_CSBRespinf has the following characteristics: %s", check_dhis_value(ira_all))


CSBRespinf_json = {
    "dataValues": ira_all.to_dict(orient="records")
}

logger.info("Importing pridec_historic_CSBRespinf into PRIDE-C instance with dryRun = %s", dryRun)

resp = post_dataElements(dhis_url = DHIS_URL, payload = CSBRespinf_json, token = DHIS_TOKEN, dryRun = dryRun)
if resp.ok:
    logger.info("Imported pridec_historic_CSBRespinf")
    logger.debug("Response: %s", resp.text)
else:
    logger.error("Failed to import pridec_historic_CSBRespinf with status code %s", resp.status_code)
    logger.error("Response: %s", resp.text)

## ------------------------ CSB Diarrhea ------------------------------
# uses same co as ira

diar_csb = get_dataElements(dhis_url = PIVOT_URL,
                      token = PIVOT_TOKEN,
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


logger.info("pridec_historic_CSBDiarrhea has the following characteristics: %s", check_dhis_value(diar_all))

CSBDiarrhea_json = {
    "dataValues": diar_all.to_dict(orient="records")
}

logger.info("Importing pridec_historic_CSBDiarrhea into PRIDE-C instance with dryRun = %s", dryRun)

resp = post_dataElements(dhis_url = DHIS_URL, payload = CSBRespinf_json, token = DHIS_TOKEN, dryRun = dryRun)
if resp.ok:
    logger.info("Imported pridec_historic_CSBDiarrhea")
    logger.debug("Response: %s", resp.text)
else:
    logger.error("Failed to import pridec_historic_CSBDiarrhea with status code %s", resp.status_code)
    logger.error("Response: %s", resp.text)