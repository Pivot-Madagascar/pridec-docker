from fastapi import Query

CONFIRM_RELAUNCH = Query(False, description="Required to relaunch an item already in success (409 confirmation_required otherwise)")
CONFIRM_OVERWRITE = Query(False, description="Required once a forecast of the cycle is in success: this job overwrites its input files (409 confirmation_required otherwise)")
