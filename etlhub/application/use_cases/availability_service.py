import json
from datetime import datetime

from etl.scripts.check_import_availability import availability_plan, availability_report
from etlhub.domain.exceptions import ETLException
from etlhub.domain.interfaces.pipeline_gate import PipelineGate


def import_params(plan: dict) -> dict[str, dict]:
    """Per import, what it reads and checks: dhis_url, task, elements, periods, org_units (availability_plan()).

    Stored with each check (AvailabilityService) and each import launch (IngestionService): two equal dicts = same parameters.
    """
    return {s["task"]: {"dhis_url": plan["dhis_url"], **s} for s in plan["imports"]}


class AvailabilityService:
    """GET /import_availability: is the data of the three imports already in DHIS2? Read only, journaled.

    A section (one import) checked by anyone in the cycle is reused while it holds (PipelineGate.reusable_availability):
    only the other sections ask DHIS2. refresh=True asks DHIS2 for all of them.
    """

    def __init__(self, gate: PipelineGate, plan=availability_plan, report=availability_report):
        self._gate = gate
        self._plan = plan
        self._report = report

    def check(self, refresh: bool = False) -> dict:
        started_at = datetime.now().isoformat(timespec="microseconds")  # a launch during the check invalidates it
        try:
            plan = self._plan()
            params = {task: json.dumps(p, sort_keys=True) for task, p in import_params(plan).items()}
            reused = {} if refresh else self._gate.reusable_availability(params)
            todo = [task for task in params if task not in reused]
            fresh = self._report(todo) if todo else None
        except Exception as e:  # missing PARENT_OU, no DHIS2 session: DHIS2 errors only mark their row
            self._gate.record_availability_check("availability_checked", {"error": str(e)[:200]})
            raise ETLException(f"Import availability check failed: {e}") from e

        checked = {s["task"]: s for s in fresh["imports"]} if fresh else {}
        stored = [{"task": t, "params": params[t], "section": s, "last_analytics": fresh["last_analytics"]}
                  for t, s in checked.items()]
        imports = [checked.get(t) or reused[t]["section"] for t in params]
        meta = self._gate.record_availability_check(
            "availability_checked" if checked else "availability_reused",
            _summary(imports, list(checked), list(reused)), stored, started_at)

        for imp in imports:  # after the store: what is stored has no origin, a reuse gets its own
            origin = meta if imp["task"] in checked else reused[imp["task"]]
            imp.update({k: origin[k] for k in ("checked_at", "checked_by", "pass_id")}, reused=imp["task"] not in checked)
        latest = max(reused.values(), key=lambda r: r["checked_at"], default=None)
        return {"dhis_url": plan["dhis_url"], "imports": imports,
                "last_analytics": fresh["last_analytics"] if fresh else latest and latest["last_analytics"]}


def _summary(imports: list[dict], checked: list[str], reused: list[str]) -> dict:
    """Journal detail: the sections checked and reused (when any), and dataElement counts over all of them."""
    elements = [el for imp in imports for el in imp["elements"]]
    return {
        **({"checked": checked} if checked else {}),
        **({"reused": reused} if reused else {}),
        "missing": sum(el["raw"] is not None and not el["imported"] for el in elements),
        "analytics_behind": sum(el["analytics_up_to_date"] is False for el in elements),
        "errors": sum(el["error"] is not None for el in elements),
    }
