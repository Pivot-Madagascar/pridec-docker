"""build_analytics job: etlhub's copy of etl/scripts/build_analytics.py and of pivot_dhis_tools.launch_analytics (v0.3.0)
without the library's 15-minute limit, which failed the job (TimeoutError) while DHIS2 went on building.

Waits for DHIS2's end however long (no job timeout: a stuck job is released from the Journal), and writes each new DHIS2
notification once to the job's log, followed live in etlui through the log WebSocket. A network cut or a 5xx while
checking is waited out (DHIS2 goes on building); a 4xx fails the job.
ponytail: a copy; the CLI (etl/) keeps the 15-minute limit. Drop it once pivot_dhis_tools can wait without limit.
"""
import logging
import time

import httpx

from etl.scripts.config import check_envvars, get_dhis_token, get_dhis_url, get_dry_run, setup_logging

logger = logging.getLogger("analytics")
POLL_SECONDS = 30  # as pivot_dhis_tools


def build_analytics() -> None:
    dhis_url, token, dry_run = get_dhis_url(), get_dhis_token(), get_dry_run()
    setup_logging()  # here, not at import: the job's stdout/stderr redirection must be active
    logger.info("Launching analytics table at %s", dhis_url)
    if dry_run:
        logger.info("DRY RUN - analytics tables will not be built")
        return
    check_envvars({"DHIS_URL": dhis_url, "DHIS_TOKEN": token})
    headers = {"Authorization": f"ApiToken {token}"}
    response = httpx.post(f"{dhis_url}/api/33/resourceTables/analytics", headers=headers, timeout=30)
    response.raise_for_status()
    endpoint = response.json()["response"]["relativeNotifierEndpoint"]
    if not endpoint.startswith("/api/"):  # the token goes to the login's DHIS2 only
        raise RuntimeError(f"Unexpected analytics status endpoint from DHIS2: {endpoint}")
    status_url = f"{dhis_url}{endpoint}"
    logger.info("Analytics build launched, status at %s, checked every %d s", status_url, POLL_SECONDS)
    seen = set()
    while True:
        time.sleep(POLL_SECONDS)
        try:
            status = httpx.get(status_url, headers=headers, timeout=30)
        except httpx.TransportError as e:  # network cut or timeout: DHIS2 goes on building
            logger.warning("DHIS2 status unreachable (%s), checking again in %d s", type(e).__name__, POLL_SECONDS)
            continue
        if status.status_code >= 500:  # DHIS2 or its proxy restarting
            logger.warning("DHIS2 status answered %d, checking again in %d s", status.status_code, POLL_SECONDS)
            continue
        status.raise_for_status()  # 4xx: the token or the task is gone, waiting won't help
        notifications = status.json()  # newest first
        for n in reversed(notifications):
            key = n.get("uid") or (n.get("time"), n.get("message"))
            if key not in seen:
                seen.add(key)
                logger.info("DHIS2: %s", n.get("message"))
        if errors := [n for n in notifications if n.get("level") == "ERROR"]:
            raise RuntimeError(f"Analytics table build failed: {errors[0].get('message')}")
        if notifications and notifications[0].get("completed"):
            logger.info("Analytics table build completed")
            return
