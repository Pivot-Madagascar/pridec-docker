"""import_gee job: the GEE climate variables chosen in the Import GEE dialog, into DHIS2, one post per variable, each
one's state kept for the dialog's "Import state" column (docs/decision-design/gee-import/gee-import.md).

etlhub's version of etl/scripts/import_gee.py (left as is for the CLI): the same GEE setup and one fetch of every
chosen variable (pridec_gee computes a source's variables together, and returns them all even when one is asked), then
a post per chosen variable of its own values only: a variable not chosen is never posted. A failed post does not stop
the others (independent variables; CREATE_AND_UPDATE: posting again is safe); the job ends in error if one failed.
States in FetchedImports under "import_gee", per pass and mode; a new import replaces them whole.
ponytail: GEE setup copied from the script; a change to one must be made to the other.
"""
import logging
from datetime import datetime

from pridec_gee import calc_date_range, fetch_climate_gee, get_dhis_geojson, post_climate
from etl.scripts.config import (GEE_SERVICE_ACCOUNT, check_envvars, get_dhis_token, get_dhis_url, get_dry_run,
                                get_gee_variables, get_parent_ou, setup_logging)
from etlhub.application.use_cases.fetch_pivot import _check_import
from etlhub.domain.interfaces.fetched_imports import FetchedImports
from etlhub.application.use_cases.ingestion_service import available_gee_variables

logger = logging.getLogger("import_gee")

TASK = "import_gee"
OU_LEVEL = 6  # fokontany, hardcoded as in the script


def _fetch(variables: list[str], url: str, token: str, parent_ou: str) -> list[dict]:
    """Every chosen variable from GEE, as DHIS2 data values (dataElement, period, orgUnit, value). The script's setup."""
    import json
    import os
    from importlib.resources import files
    import ee

    key = os.path.join(os.getcwd(), ".gee-private-key.json")
    if not os.path.isfile(key):
        raise FileNotFoundError(f"'.gee-private-key.json' not found in {os.getcwd()}")
    ee.Initialize(ee.ServiceAccountCredentials(GEE_SERVICE_ACCOUNT, key))
    with open(files("pridec_gee").joinpath("data/pivot_major_rice.geojson")) as f:
        rice_fields = ee.FeatureCollection(json.load(f))
    org_units = ee.FeatureCollection(get_dhis_geojson(parent_ou=parent_ou, ou_level=OU_LEVEL, dhis_url=url, dhis_token=token))
    frame = fetch_climate_gee(date_range=calc_date_range(start_months_ago=3, end_on_last_day=True), orgUnit=org_units,
                              variables=variables, rice_features=rice_fields)
    if frame is None:  # pridec_gee logs why (floodedRice without rice fields) and returns nothing
        raise RuntimeError("GEE returned no data")
    return frame.to_dict(orient="records")


def _state(status: str, dry_run: bool, error: str | None = None, rows: int | None = None) -> dict:
    return {"status": status, "at": datetime.now().isoformat(timespec="seconds"), "dry_run": dry_run, "error": error,
            "rows": rows}


def _save(imports: FetchedImports, states: dict[str, dict]) -> None:
    imports.save(TASK, [{"variable": name, **state} for name, state in states.items()])


def import_gee(imports: FetchedImports) -> None:
    setup_logging()  # here, not at import: the job's stdout/stderr redirection must be active
    variables = get_gee_variables()  # the pass's: chosen in the Import GEE dialog
    url, token, parent_ou, dry_run = get_dhis_url(), get_dhis_token(), get_parent_ou(), get_dry_run()
    check_envvars({"DHIS_TOKEN": token, "DHIS_URL": url, "PARENT_OU": parent_ou,
                   "GEE_SERVICE_ACCOUNT": GEE_SERVICE_ACCOUNT, "GEE_VARIABLES": variables})
    states = {name: _state("running", dry_run) for name in variables}
    _save(imports, states)
    try:
        rows = _fetch(variables, url, token, parent_ou)
    except Exception as e:
        _save(imports, {name: _state("failed", dry_run, f"GEE fetch failed: {e}") for name in variables})
        raise
    failed = []
    for name in variables:
        values = [row for row in rows if row["dataElement"] == name]
        if not values:
            logger.warning("%s: no value from GEE, nothing to post", name)
            states[name] = _state("empty", dry_run, rows=0)
        else:
            logger.info("Posting %s (%d values) to %s, dryRun=%s", name, len(values), url, dry_run)
            try:
                _check_import(name, post_climate(base_url=url, payload={"dataValues": values}, token=token, dryRun=dry_run))
                states[name] = _state("imported", dry_run, rows=len(values))
            except Exception as e:
                logger.error("%s: %s", name, e)
                states[name] = _state("failed", dry_run, str(e))
                failed.append(name)
        _save(imports, states)
    if failed:
        raise RuntimeError(f"GEE import failed for {', '.join(failed)}")


def gee_imports(imports: FetchedImports, chosen: str | None) -> list[dict]:
    """Every GEE variable: whether the pass imports it (its gee_variables, comma-separated; None: all of them) and the
    state of its last import in the pass (None: never imported there)."""
    states = {s["variable"]: s for s in imports.load(TASK)}
    picked = chosen.split(",") if chosen else None
    return [{"variable": name, "chosen": picked is None or name in picked, "state": states.get(name)}
            for name in available_gee_variables()]
