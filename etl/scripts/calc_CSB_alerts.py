from .config import DHIS_TOKEN, DHIS_URL, dryRun, setup_logging, check_envvars
from pivot_dhis_tools import post_dataElements, pridec_calc_CSB_alerts
import os
import json
import logging

def calc_csb_alerts():
    setup_logging()

    logger = logging.getLogger("calc_CSB_alerts")

    logger.info("Estimating and POSTing 'CSB en vigilance' on %s", DHIS_URL)

    check_envvars(required_vars = {
                'DHIS_TOKEN': DHIS_TOKEN,
                'DHIS_URL': DHIS_URL})

    #automatically does for current month
    json_alert = pridec_calc_CSB_alerts(dhis_url = DHIS_URL,
                                    token = DHIS_TOKEN)

    post_dataElements(dhis_url = DHIS_URL, payload = json_alert,
                       token= DHIS_TOKEN, dryRun=dryRun)

if __name__ == "__main__":
    calc_csb_alerts()