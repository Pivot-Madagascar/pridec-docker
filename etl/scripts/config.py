from dotenv import load_dotenv
import os

load_dotenv(override=False)

#run configurations
dryRun = os.getenv('DRYRUN', 'true').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

#dhis api info
DHIS_URL = os.getenv('DHIS_URL')
if DHIS_URL is not None:
    DHIS_URL = DHIS_URL.rstrip('/')
DHIS_TOKEN = os.getenv('DHIS_TOKEN')
DHIS_USER = os.getenv('DHIS_USER')
DHIS_PWD = os.getenv('DHIS_PWD')
PIVOT_URL = os.environ.get('PIVOT_URL')
if PIVOT_URL is not None:
    PIVOT_URL = PIVOT_URL.rstrip('/')
PIVOT_TOKEN = os.environ.get('PIVOT_TOKEN')

PARENT_OU = os.environ.get('PARENT_OU')
OU_LEVEL = os.environ.get('OU_LEVEL')
DISEASE_CODE = os.environ.get('DISEASE_CODE')

#gee info
GEE_PROJECT = os.environ.get('GEE_PROJECT')
GEE_SERVICE_ACCOUNT = os.environ.get('GEE_SERVICE_ACCOUNT')



# LOGGING SETUP
def setup_logging():
    import logging

    from config import LOG_LEVEL

    logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', 
                        level=getattr(logging, LOG_LEVEL, logging.INFO),
                        datefmt="%Y-%m-%dT%H:%M:%S",
                        force=True)

#throw errors for missing environmental variables
def check_envvars(required_vars: dict):
    for name, value in required_vars.items():
        if value is None or value == "":
            raise EnvironmentError(f"Required environment variable '{name}' is missing. Verify your `.env` file.")
    return