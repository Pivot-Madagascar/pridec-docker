
from datetime import date
from dateutil.relativedelta import relativedelta
import logging
import requests
#update to pivot_dhis_tools package
from utils import create_period_range

from config import  PIVOT_URL, PIVOT_TOKEN, dryRun, DHIS_URL, DHIS_TOKEN

import logging
logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

period_list = create_period_range(start = (date.today()-relativedelta(months=2)))

logger.info("periods %s", period_list)

headers = {'Authorization': f'ApiToken {DHIS_TOKEN}'} 

url =  (
    f"{DHIS_URL.rstrip('/')}/api/dataElements"
    f"?filter=code:like:pridec_climate"
    f"&fields=id,code,displayName,description"
    f"&paging=false"
)
resp = requests.get(url, headers=headers, )
de_info = resp.json().get('dataElements')

logger.info(de_info)