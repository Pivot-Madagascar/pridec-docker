"""import_pivot_com / import_pivot_csb jobs: fetch and check Pivot case counts, write them, post nothing to DHIS2.
approve_imports job (post_pivot_imports): posts the data elements the user chose among them (POST /pipeline/imports/approve).

etlhub's copy of etl/scripts/import_pivot_COM_etlhub.py and import_pivot_CSB_etlhub.py, whose code runs at import
(`from config import`: needs etl/scripts on sys.path, absent in the worker, and reads PARENT_OU from .env, not the pass).
The scripts write <dataElement>_fetched.json and _flags.json in ./input/temp_fetch; etlhub keeps the same content in
Redis instead (FetchedImports, since 2026-11-23), per pass and mode: opening a forecast run empties input/, a logout
loses Pinia, neither loses it. A new fetch of an import replaces its last one whole; an import never fetched has none.
PIVOT_URL and PARENT_OU come from etlhub's config (GET /api/config, Redis; PARENT_OU fixed by the pass), not from .env;
PIVOT_TOKEN, a secret, from the environment only.
ponytail: two copies of the same steps; a change to one must be made to the other.
"""
import logging

from pivot_dhis_tools import fetch_pivot_com_etlhub, fetch_pivot_csb_etlhub, post_dataElements
from etl.scripts import config
from etl.scripts.config import (PIVOT_TOKEN, check_envvars, get_dhis_token, get_dhis_url, get_dry_run,
                                get_parent_ou, setup_logging)
from etlhub.application.use_cases.check_import_availability import COM_ELEMENTS, CSB_ELEMENTS
from etlhub.domain.interfaces.fetched_imports import FetchedImports

logger = logging.getLogger("import_pivot")

PRIOR_MONTHS = 8  # as the scripts' __main__ (and check_import_availability's periods)
PIVOT_ELEMENTS = {"import_pivot_com": COM_ELEMENTS, "import_pivot_csb": CSB_ELEMENTS}  # the files each fetch writes


def _store() -> FetchedImports:
    # The composition root's adapter, read when called: the jobs and the module functions get no injection.
    from etlhub.core.dependencies import get_fetched_imports  # not at import: dependencies imports this module's users
    return get_fetched_imports()


def _save(task: str, results: list[dict]) -> None:
    """The import's answer (the library's items), replacing its previous one in the pass."""
    _store().save(task, results)
    for item in results:
        logger.info("%s: %d rows, %s", item["dataElement"], len(item["fetched_data"]),
                    "FLAGGED" if item["summary"]["flagged"] else "ok")


def pivot_url() -> str | None:
    """PIVOT_URL of the editable config (Redis under etlhub). config._get, not an imported name: etlhub replaces it."""
    url = config._get("PIVOT_URL")
    return url.rstrip("/") if url else None


def has_pivot_token() -> bool:
    return bool(PIVOT_TOKEN)


def import_pivot_com() -> None:
    setup_logging()  # here, not at import: the job's stdout/stderr redirection must be active
    url, parent_ou = pivot_url(), get_parent_ou()  # the config's, the pass's
    check_envvars({"PIVOT_TOKEN": PIVOT_TOKEN, "PIVOT_URL": url, "PARENT_OU": parent_ou})
    _save("import_pivot_com", fetch_pivot_com_etlhub(pivot_token=PIVOT_TOKEN, pivot_url=url,
                                                     prior_months=PRIOR_MONTHS, parent_ou=parent_ou))


def import_pivot_csb() -> None:
    setup_logging()
    url = pivot_url()
    check_envvars({"PIVOT_TOKEN": PIVOT_TOKEN, "PIVOT_URL": url})
    _save("import_pivot_csb", fetch_pivot_csb_etlhub(pivot_token=PIVOT_TOKEN, pivot_url=url, prior_months=PRIOR_MONTHS))


def _fetched() -> dict[str, dict]:
    """Every element the Pivot imports fetched in this pass and mode: dataElement -> its item."""
    return {item["dataElement"]: item for task in PIVOT_ELEMENTS for item in _store().load(task)}


def fetched_imports() -> list[dict]:
    """Per Pivot import, the elements of its last fetch in the pass (only those, in its list's order): rows and check."""
    items = {task: {i["dataElement"]: i for i in _store().load(task)} for task in PIVOT_ELEMENTS}
    return [{"task": task, "elements": [_element(items[task][name]) for name in names if name in items[task]]}
            for task, names in PIVOT_ELEMENTS.items()]


def _element(item: dict) -> dict:
    summary = item["summary"]
    return {"data_element": item["dataElement"], "rows": len(item["fetched_data"]), "flagged": bool(summary.get("flagged")),
            "text": summary.get("text"), "error": summary.get("error")}


def not_fetched(elements: list[str]) -> list[str]:
    fetched = _fetched()
    return [name for name in elements if name not in fetched]


def post_pivot_imports(elements: list[str]) -> None:
    """approve_imports job: posts each chosen element's fetched values to DHIS2, with the job's DRYRUN (the pass's).
    A failed post stops the job (error): the elements posted before it stay (CREATE_AND_UPDATE: posting again is safe)."""
    setup_logging()
    url, token, dry_run = get_dhis_url(), get_dhis_token(), get_dry_run()
    if not elements:
        logger.info("Imports approved without any data element: nothing posted to %s", url)
    fetched = _fetched()
    for name in elements:
        payload = {"dataValues": fetched[name]["fetched_data"]}
        if not payload["dataValues"]:
            logger.warning("%s: no value fetched, nothing to post", name)
            continue
        logger.info("Posting %s (%d values) to %s, dryRun=%s", name, len(payload["dataValues"]), url, dry_run)
        _check_import(name, post_dataElements(dhis_url=url, payload=payload, token=token, dryRun=dry_run))


def _check_import(name: str, response) -> None:
    """post_dataElements raises on an HTTP error; DHIS2 may still answer 200 with an import status ERROR."""
    try:
        body = response.json()
    except ValueError:
        body = {}
    summary = body.get("response") or body
    logger.info("%s: %s, %s", name, summary.get("status"), summary.get("importCount"))
    for conflict in summary.get("conflicts") or []:
        logger.warning("%s: conflict %s", name, conflict)
    if summary.get("status") == "ERROR" or body.get("status") == "ERROR":
        raise RuntimeError(f"DHIS2 refused {name}: {body.get('message') or summary.get('description')}")
