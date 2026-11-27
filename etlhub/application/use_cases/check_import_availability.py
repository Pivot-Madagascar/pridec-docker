"""GET /import_availability: is the data of import_gee / import_pivot_com / import_pivot_csb already in DHIS2? Read only."""
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date


from etlhub.domain.interfaces.dhis2_reader import DHIS2Reader
from etlhub.domain.interfaces.import_settings import ImportSettings

# ponytail: periods, orgUnits and dataElements are copied from import_gee and from pivot_dhis_tools.pridec.import_pivot
# (COM_ELEMENTS, CSB_IDS, CSB_ELEMENTS, used by fetch_pivot.py). Keep in sync when one of them changes (tests/test_library_constants_sync.py checks the installed library).
CSB_IDS = [
    "D9UWDj19ljP", "U1YeJp3NDNV", "DDR2w1c1GyE", "uWoBok9YyvB",
    "O1wNJut8eci", "FGM6Ric1YnC", "r4U7PhBKR7S", "RRe6ic0AU1Z",
    "okDqhh9n4yT", "z6kDxHwInUT", "h0z1bKoHDrU", "Pi2y9HFBDRj",
    "pczrAub8lnt", "YCvVB1VwWi0", "hXuxS0MOq3b", "mBZLeZ7Irx6",
    "WCqkkkKNJEi", "EE6WwIMgQ0F", "M38BJM8ju1A", "ZPvH8UsgwYv",
    "QHPyq70qulM"
]
COM_ELEMENTS = ["pridec_historic_COMMalaria", "pridec_historic_COMRespinf", "pridec_historic_COMDiarrhea"]
CSB_ELEMENTS = ["pridec_historic_CSBMalaria", "pridec_historic_CSBRespinf", "pridec_historic_CSBDiarrhea"]

logger = logging.getLogger("check_import_availability")


def _raw_counts(dhis2: DHIS2Reader, url: str, token: str, code: str, periods: list[str], org_units: list[str],
                children: bool):
    """orgUnits with a stored value per period, and the latest lastUpdated of these values.

    ponytail: children=true counts every descendant of PARENT_OU, not only level 6; the imported dataElements
    only have level-6 values today. Filter on the orgUnit level if another level ever gets them.
    """
    values = dhis2.data_values(url, token, {
        "dataElement": code, "inputDataElementIdScheme": "CODE", "period": periods,
        "orgUnit": org_units, "children": "true" if children else "false",
    })
    counts = {pe: len({v["orgUnit"] for v in values if v["period"] == pe}) for pe in periods}
    return counts, max((v["lastUpdated"] for v in values), default=None)


def _analytics_counts(dhis2: DHIS2Reader, url: str, token: str, code: str, periods: list[str],
                      ou_query: str) -> dict[str, int]:
    rows = dhis2.analytics(url, token, code, periods, ou_query)
    return {pe: len({r["ou"] for r in rows if r["pe"] == pe}) for pe in periods}


def _check_element(dhis2: DHIS2Reader, url, token, code, periods, org_units, children, ou_query) -> dict:
    """One dataElement: its own requests, so an unknown code or a failing analytics only marks this row."""
    element = {"code": code, "raw": None, "analytics": None, "last_updated": None,
               "imported": False, "analytics_up_to_date": None, "error": None}
    try:
        element["raw"], element["last_updated"] = _raw_counts(dhis2, url, token, code, periods, org_units, children)
        element["imported"] = all(element["raw"].values())
        element["analytics"] = _analytics_counts(dhis2, url, token, code, periods, ou_query)
        element["analytics_up_to_date"] = element["analytics"] == element["raw"]
    except Exception as e:
        logger.error("could not check %s: %s", code, e)
        element["error"] = str(e)
    return element


def _last_analytics(dhis2: DHIS2Reader, url: str, token: str) -> str | None:
    """lastAnalyticsTableSuccess of /api/system/info (server local time), None if DHIS2 does not give it."""
    try:
        return dhis2.system_info(url, token).get("lastAnalyticsTableSuccess")
    except Exception as e:
        logger.warning("could not read the last analytics build: %s", e)
        return None


def _last_months(n: int, today: date | None = None) -> list[str]:
    """The n months before the current one, oldest first ("YYYYMM"): what pivot_dhis_tools.create_period_range gives
    from n months ago (import_pivot_*: 8; import_gee: 3, = calc_date_range(start_months_ago=3))."""
    today = today or date.today()
    index = today.year * 12 + today.month - 1  # months since year 0, current month
    return [f"{i // 12}{i % 12 + 1:02d}" for i in range(index - n, index)]


def availability_plan(settings: ImportSettings) -> dict:
    """What each section checks, without any DHIS2 request: etlhub compares it to decide whether a stored check still holds.

    Raises EnvironmentError when DHIS_URL, DHIS_TOKEN or PARENT_OU is missing.
    """
    s = settings.read()
    fokontany = f"ou:LEVEL-6;{';'.join(p.strip() for p in s['parent_ou'].split(',') if p.strip())}"
    pivot_periods, gee_periods = _last_months(8), _last_months(3)
    return {"dhis_url": s["dhis_url"], "imports": [
        {"task": "import_gee", "elements": s["gee_variables"], "periods": gee_periods, "org_units": fokontany},
        {"task": "import_pivot_com", "elements": COM_ELEMENTS, "periods": pivot_periods, "org_units": fokontany},
        {"task": "import_pivot_csb", "elements": CSB_ELEMENTS, "periods": pivot_periods, "org_units": f"ou:{';'.join(CSB_IDS)}"},
    ]}


def _raw_org_units(ou_query: str) -> tuple[list[str], bool]:
    """Raw-data orgUnits of an analytics ou query: "ou:LEVEL-6;A;B" -> (["A", "B"], children=True), "ou:X;Y" -> (["X", "Y"], False)."""
    items = ou_query.removeprefix("ou:").split(";")
    return (items[1:], True) if items[0].startswith("LEVEL-") else (items, False)


def availability_report(dhis2: DHIS2Reader, settings: ImportSettings, tasks: list[str] | None = None) -> dict:
    """Read-only report of what import_gee / import_pivot_com / import_pivot_csb would import, as DHIS2 has it now.

    `tasks` limits it to these sections (all by default). Raises EnvironmentError like availability_plan;
    a DHIS2 error only marks its row.
    """
    plan = availability_plan(settings)  # the token stays out of the plan: the plan is stored with each check
    DHIS_URL, DHIS_TOKEN = plan["dhis_url"], settings.read()["dhis_token"]
    imports = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for section in plan["imports"]:
            if tasks is not None and section["task"] not in tasks:
                continue
            periods, ou_query = section["periods"], section["org_units"]
            org_units, children = _raw_org_units(ou_query)
            rows = pool.map(lambda code: _check_element(dhis2, DHIS_URL, DHIS_TOKEN, code, periods, org_units, children,
                                                        ou_query), section["elements"])
            imports.append({"task": section["task"], "periods": periods, "org_units": ou_query, "elements": list(rows)})

    return {
        "dhis_url": DHIS_URL,
        "last_analytics": _last_analytics(dhis2, DHIS_URL, DHIS_TOKEN),
        "imports": imports,
    }
