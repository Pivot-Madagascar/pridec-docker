"""import_pivot_com / import_pivot_csb jobs: fetch and check Pivot case counts, write them, post nothing to DHIS2.
approve_imports job (post_pivot_imports): posts the data elements the user chose among them (POST /pipeline/imports/approve).

etlhub's copy of etl/scripts/import_pivot_COM_etlhub.py and import_pivot_CSB_etlhub.py, whose code runs at import
(`from config import`: needs etl/scripts on sys.path, absent in the worker, and reads PARENT_OU from .env, not the pass).
Same files (etl/etlhub-documentation.md): <dataElement>_fetched.json and <dataElement>_flags.json, but in the mode's
input/temp_fetch (test/input/temp_fetch in test mode) instead of the scripts' ./inputs/temp_fetch.
ponytail: two copies of the same steps; a change to one must be made to the other.
"""
import json
import logging
from pathlib import Path

from pivot_dhis_tools import fetch_pivot_com_etlhub, fetch_pivot_csb_etlhub, post_dataElements
from etl.scripts.config import (PIVOT_TOKEN, PIVOT_URL, check_envvars, get_dhis_token, get_dhis_url, get_dry_run,
                                get_parent_ou, setup_logging)
from etlhub.application.use_cases.check_import_availability import COM_ELEMENTS, CSB_ELEMENTS
from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir

logger = logging.getLogger("import_pivot")

PRIOR_MONTHS = 8  # as the scripts' __main__ (and check_import_availability's periods)
PIVOT_ELEMENTS = {"import_pivot_com": COM_ELEMENTS, "import_pivot_csb": CSB_ELEMENTS}  # the files each fetch writes


def fetch_dir() -> Path:
    return work_dir(get_settings().data_dir, "input", current_test_mode()) / "temp_fetch"


def _save(results: list[dict]) -> None:
    """Each item as <dataElement>_fetched.json ({"dataValues": [...]}) and <dataElement>_flags.json (its summary)."""
    out = fetch_dir()
    out.mkdir(parents=True, exist_ok=True)
    for item in results:
        name, summary = item["dataElement"], item["summary"]
        (out / f"{name}_fetched.json").write_text(json.dumps({"dataValues": item["fetched_data"]}, indent=2, default=str))
        (out / f"{name}_flags.json").write_text(json.dumps(summary, indent=2, default=str))
        logger.info("%s: %d rows, %s", name, len(item["fetched_data"]), "FLAGGED" if summary["flagged"] else "ok")


def import_pivot_com() -> None:
    setup_logging()  # here, not at import: the job's stdout/stderr redirection must be active
    parent_ou = get_parent_ou()  # the pass's
    check_envvars({"PIVOT_TOKEN": PIVOT_TOKEN, "PIVOT_URL": PIVOT_URL, "PARENT_OU": parent_ou})
    _save(fetch_pivot_com_etlhub(pivot_token=PIVOT_TOKEN, pivot_url=PIVOT_URL,
                                 prior_months=PRIOR_MONTHS, parent_ou=parent_ou))


def import_pivot_csb() -> None:
    setup_logging()
    check_envvars({"PIVOT_TOKEN": PIVOT_TOKEN, "PIVOT_URL": PIVOT_URL})
    _save(fetch_pivot_csb_etlhub(pivot_token=PIVOT_TOKEN, pivot_url=PIVOT_URL, prior_months=PRIOR_MONTHS))


def fetched_imports() -> list[dict]:
    """Per Pivot import, the elements its last fetch wrote in this mode's folder (only those): rows and check result.
    The folder is the pass's: a new pass empties input/ (carried imports included), a pause keeps it for the resume."""
    out = fetch_dir()
    return [{"task": task, "elements": [_element(out, name) for name in names if (out / f"{name}_flags.json").is_file()]}
            for task, names in PIVOT_ELEMENTS.items()]


def _element(out: Path, name: str) -> dict:
    flags = json.loads((out / f"{name}_flags.json").read_text())  # written after _fetched.json: both are there
    rows = len(json.loads((out / f"{name}_fetched.json").read_text())["dataValues"])
    return {"data_element": name, "rows": rows, "flagged": bool(flags.get("flagged")),
            "text": flags.get("text"), "error": flags.get("error")}


def not_fetched(elements: list[str]) -> list[str]:
    return [name for name in elements if not (fetch_dir() / f"{name}_fetched.json").is_file()]


def post_pivot_imports(elements: list[str]) -> None:
    """approve_imports job: posts each chosen element's fetched values to DHIS2, with the job's DRYRUN (the pass's).
    A failed post stops the job (error): the elements posted before it stay (CREATE_AND_UPDATE: posting again is safe)."""
    setup_logging()
    url, token, dry_run = get_dhis_url(), get_dhis_token(), get_dry_run()
    if not elements:
        logger.info("Imports approved without any data element: nothing posted to %s", url)
    for name in elements:
        payload = json.loads((fetch_dir() / f"{name}_fetched.json").read_text())
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
