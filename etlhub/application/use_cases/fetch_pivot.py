"""import_pivot_com / import_pivot_csb jobs: fetch and check Pivot case counts, write them, post nothing to DHIS2.
approve_imports job (post_pivot_imports, Celery): posts the data elements the user chose among them (POST /pipeline/imports/approve).

etlhub's copy of etl/scripts/import_pivot_COM_etlhub.py and import_pivot_CSB_etlhub.py, whose code runs at import
(`from config import`: needs etl/scripts on sys.path, absent in the worker, and reads PARENT_OU from .env, not the pass).
The scripts write <dataElement>_fetched.json and _flags.json in ./input/temp_fetch; etlhub keeps the same content in
Redis instead (FetchedImports, since 2026-11-23), per pass and mode: opening a forecast run empties input/, a logout
loses Pinia, neither loses it. A new fetch of an import replaces its last one whole; an import never fetched has none.
PIVOT_URL and PARENT_OU come from etlhub's config (both fixed by the pass, from Redis when it started), not from .env;
PIVOT_TOKEN, a secret, from the environment only.
ponytail: two copies of the same steps; a change to one must be made to the other.
"""
import logging
from datetime import datetime

from pivot_dhis_tools import fetch_pivot_com_etlhub, fetch_pivot_csb_etlhub, post_dataElements
from etl.scripts import config
from etl.scripts.config import (PIVOT_TOKEN, check_envvars, get_dhis_token, get_dhis_url, get_dry_run,
                                get_parent_ou, setup_logging)
from etlhub.application.use_cases.check_import_availability import COM_ELEMENTS, CSB_ELEMENTS
from etlhub.domain.interfaces.fetched_imports import FetchedImports

logger = logging.getLogger("import_pivot")

PRIOR_MONTHS = 8  # as the scripts' __main__ (and check_import_availability's periods)
PIVOT_ELEMENTS = {"import_pivot_com": COM_ELEMENTS, "import_pivot_csb": CSB_ELEMENTS}  # the files each fetch writes


# Every function reading or writing the fetched data takes the FetchedImports port: the jobs get the worker's adapter
# (infrastructure/tasks.py, through run_etl_job), the API the composition root's (Depends(get_fetched_imports)).


def _save(imports: FetchedImports, task: str, results: list[dict]) -> None:
    """The import's answer (the library's items), replacing its previous one in the pass."""
    imports.save(task, results)
    for item in results:
        logger.info("%s: %d rows, %s", item["dataElement"], len(item["fetched_data"]),
                    "FLAGGED" if item["summary"]["flagged"] else "ok")


def pivot_url() -> str | None:
    """PIVOT_URL fixed by the pass (since 2026-11-27; a pass from before: the editable config, Redis) under etlhub.
    config._get, not an imported name: etlhub replaces it."""
    url = config._get("PIVOT_URL")
    return url.rstrip("/") if url else None


def has_pivot_token() -> bool:
    return bool(PIVOT_TOKEN)


def import_pivot_com(imports: FetchedImports) -> None:
    setup_logging()  # here, not at import: the job's stdout/stderr redirection must be active
    url, parent_ou = pivot_url(), get_parent_ou()  # both the pass's
    check_envvars({"PIVOT_TOKEN": PIVOT_TOKEN, "PIVOT_URL": url, "PARENT_OU": parent_ou})
    _save(imports, "import_pivot_com", fetch_pivot_com_etlhub(pivot_token=PIVOT_TOKEN, pivot_url=url,
                                                     prior_months=PRIOR_MONTHS, parent_ou=parent_ou))


def import_pivot_csb(imports: FetchedImports) -> None:
    setup_logging()
    url = pivot_url()
    check_envvars({"PIVOT_TOKEN": PIVOT_TOKEN, "PIVOT_URL": url})
    _save(imports, "import_pivot_csb", fetch_pivot_csb_etlhub(pivot_token=PIVOT_TOKEN, pivot_url=url, prior_months=PRIOR_MONTHS))


def _fetched(imports: FetchedImports) -> dict[str, dict]:
    """Every element the Pivot imports fetched in this pass and mode: dataElement -> its item."""
    return {item["dataElement"]: item for task in PIVOT_ELEMENTS for item in imports.load(task)}


def fetched_imports(imports: FetchedImports) -> list[dict]:
    """Per Pivot import, the elements of its last fetch in the pass (only those, in its list's order): rows and check."""
    items = {task: {i["dataElement"]: i for i in imports.load(task)} for task in PIVOT_ELEMENTS}
    return [{"task": task, "elements": [_element(items[task][name]) for name in names if name in items[task]]}
            for task, names in PIVOT_ELEMENTS.items()]


def _element(item: dict) -> dict:
    summary = item["summary"]
    return {"data_element": item["dataElement"], "rows": len(item["fetched_data"]), "flagged": bool(summary.get("flagged")),
            "text": summary.get("text"), "error": summary.get("error"), "post": item.get("post")}


def not_fetched(imports: FetchedImports, elements: list[str]) -> list[str]:
    fetched = _fetched(imports)
    return [name for name in elements if name not in fetched]


def _mark(imports: FetchedImports, name: str, status: str, dry_run: bool, error: str | None = None) -> None:
    """Keeps an element's post state with its fetched data (`post`, shown per line in the approval): posted, empty
    (nothing to post) or failed. Until a new fetch of its import replaces the data, and the state with it."""
    for task in PIVOT_ELEMENTS:
        items = imports.load(task)
        for item in items:
            if item["dataElement"] == name:
                item["post"] = {"status": status, "at": datetime.now().isoformat(timespec="seconds"), "dry_run": dry_run,
                                "error": error}
                imports.save(task, items)
                return


def post_pivot_imports(imports: FetchedImports, elements: list[str]) -> str:
    """approve_imports job (Celery since 2026-11-27): posts each chosen element's fetched values to DHIS2, with the
    job's DRYRUN (the mode's). A failed post stops the job (error): the elements posted before it stay
    (CREATE_AND_UPDATE: posting again is safe). Each element's outcome is kept with it (_mark), for the approval's
    per-line state (GET /pipeline/imports/fetched, read after the job). Returns the job's end message."""
    setup_logging()
    url, token, dry_run = get_dhis_url(), get_dhis_token(), get_dry_run()
    if not elements:
        logger.info("Imports approved without any data element: nothing posted to %s", url)
    fetched = _fetched(imports)
    for name in elements:
        payload = {"dataValues": fetched[name]["fetched_data"]}
        if not payload["dataValues"]:
            logger.warning("%s: no value fetched, nothing to post", name)
            _mark(imports, name, "empty", dry_run)
            continue
        logger.info("Posting %s (%d values) to %s, dryRun=%s", name, len(payload["dataValues"]), url, dry_run)
        try:
            _check_import(name, post_dataElements(dhis_url=url, payload=payload, token=token, dryRun=dry_run))
        except Exception as e:
            _mark(imports, name, "failed", dry_run, str(e))
            raise
        _mark(imports, name, "posted", dry_run)
    return f"Imports approved, posted: {', '.join(elements) or 'nothing'}"


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
