from config import DHIS_TOKEN, DHIS_URL,  setup_logging
from requests.auth import HTTPBasicAuth
import logging
from pivot_dhis_tools import launch_analytics

setup_logging()
logger = logging.getLogger("analytics")

logger.info("Launching analytics table at %s", DHIS_URL)

launch_analytics(dhis_url=DHIS_URL,
                 token=DHIS_TOKEN,
                 verbose=True)