import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import logging
#update to pivot_dhis_tools package
from pivot_dhis_tools import get_dataElements, create_period_range, check_dhis_value, post_dataElements

def print_help():
    print(f"""
Task: import_pivot_COM

Usage:
-   Import disease cases reported at community health sites during prior three months from Pivot DHIS2 instance to PRIDE-C instance

Notes:
-   This requires `PIVOT_URL` and `PIVOT_TOKEN` in .env
-   The fokontany imported are all level 6 orgUnits under `PARENT_OU` (comma-separated for several) in the Pivot instance.
""")

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(add_help=False) # disable default help
    parser.add_argument("--help", "-h", action="store_true")
    return parser.parse_args()

def import_pivot_com():
    from .config import get_dhis_url, get_dhis_token, get_dry_run,  get_parent_ou, PIVOT_URL, PIVOT_TOKEN, setup_logging, check_envvars

    DHIS_URL = get_dhis_url()
    DHIS_TOKEN = get_dhis_token()
    DRYRUN = get_dry_run()
    PARENT_OU = get_parent_ou()

    setup_logging()

    logger = logging.getLogger("import_pivot_COM")

    check_envvars(required_vars = {
                'DHIS_TOKEN': DHIS_TOKEN,
                'DHIS_URL': DHIS_URL,
                'PIVOT_TOKEN': PIVOT_TOKEN,
                'PIVOT_URL': PIVOT_URL,
                'PARENT_OU' : PARENT_OU
            }
    )

    logger.info("Importing COM Case Data from %s into %s", PIVOT_URL, DHIS_URL)

    if DRYRUN:
        logger.info("DRY RUN — no changes will be made")
    else:
        logger.info("NORMAL RUN - data will be imported into instance")

    period_list = create_period_range(start = (date.today()-relativedelta(months=8)))

    
    com_org_query = f"ou:LEVEL-6;{';'.join(p.strip() for p in PARENT_OU.split(',') if p.strip())}"
    logger.info("Importing level 6 orgUnits (fokontany) under %s", PARENT_OU)

    ##  -------------------Total Consultations ---------------
    # This is used to identify missing data vs. zeroes
    # lq38tLcfEi7 - RMA_COM_PCIMEc Nombre d'enfants reçu au site 

    com_get = get_dataElements(dhis_url = PIVOT_URL,
                        token = PIVOT_TOKEN,
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
    
    logger.info("Getting pridec_historic_COMMalaria")
    
    mal_get = get_dataElements(dhis_url = PIVOT_URL,
                        token = PIVOT_TOKEN,
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
    
    logger.info("pridec_historic_COMMalaria has the following characteristics: %s", check_dhis_value(mal_all))
    # check_dhis_value(mal_all)
    
    COMMalaria_json = {
        "dataValues": mal_all.to_dict(orient="records")
    }
    
    logger.info("Importing pridec_historic_COMMalaria into PRIDE-C instance with dryRun = %s", DRYRUN)
    
    resp = post_dataElements(dhis_url = DHIS_URL, payload = COMMalaria_json, token = DHIS_TOKEN, dryRun = DRYRUN)
    if resp.ok:
        logger.info(f"Imported pridec_historic_COMMalaria")
        logger.debug("Response: %s", resp.text)
    else:
        logger.error(f"Failed to import pridec_historic_COMMalaria with status code %s", resp.status_code)
        logger.error("Response: %s", resp.text)
    
    ## ----------------COM IRA ---------------------
    #' hJ5pa6wO4nJ : RMA_COM_PCIMEc Nombre d’enfants présentant de pneumonie 
    #' CmDXCmmywrj : RMA_COM_PCIMEc Nombre d’enfants présentant de  toux ou rhume
    
    logger.info("Getting pridec_historic_COMRespinf")
    
    ira_get = get_dataElements(dhis_url = PIVOT_URL,
                            token = PIVOT_TOKEN,
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
    
    logger.info("pridec_historic_COMRespinf has the following characteristics: %s", check_dhis_value(ira_all))
    
    COMRespinf_json = {
        "dataValues": ira_all.to_dict(orient="records")
    }
    
    logger.info("Importing pridec_historic_COMRespinf into PRIDE-C instance with dryRun = %s", DRYRUN)
    
    resp = post_dataElements(dhis_url = DHIS_URL, payload = COMRespinf_json, token = DHIS_TOKEN, dryRun = DRYRUN)
    
    if resp.ok:
        logger.info(f"Imported pridec_historic_COMRespinf")
        logger.debug("Response: %s", resp.text)
    else:
        logger.error(f"Failed to import pridec_historic_COMRespinf with status code %s", resp.status_code)
        logger.error("Response: %s", resp.text)
    
    # -------------------- COM Diarrhea -------------------
    
    #' DjsQEzPDAoN : RMA_COM_PCIMEc Nombre d’enfants présentant de diarrhée avec signes de danger
    #' f4hrhsiz49l : RMA_COM_PCIMEc Nombre d’enfants présentant de diarrhée simple
    
    logger.info("Getting pridec_historic_COMDiarrhea")
    
    diar_get = get_dataElements(dhis_url = PIVOT_URL,
                            token = PIVOT_TOKEN,
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
    
    logger.info("pridec_historic_COMDiarrhea has the following characteristics: %s", check_dhis_value(diar_all))
    
    COMDiarrhea_json = {
        "dataValues": diar_all.to_dict(orient="records")
    }
    
    logger.info("Importing pridec_historic_COMDiarrhea into PRIDE-C Instance with dryRun = %s", DRYRUN)
    
    resp = post_dataElements(dhis_url = DHIS_URL, payload = COMDiarrhea_json, token = DHIS_TOKEN, dryRun = DRYRUN)
    
    if resp.ok:
        logger.info(f"Imported pridec_historic_COMDiarrhea")
        logger.debug("Response: %s", resp.text)
    else:
        logger.error(f"Failed to import pridec_historic_COMDiarrhea with status code %s", resp.status_code)
        logger.error("Response: %s", resp.text)

if __name__ == "__main__":
    args = parse_args()
    if args.help:
        print_help()
        exit(0)
    import_pivot_com()