"""The pipeline cycle: steps, items with their prerequisites, forecast runs. Pure, no I/O.

Rules (etlhub/docs/decision-design/pipeline-checkpoints/pipeline-checkpoints.md):
- R1 every item is mandatory; config.json is one item per disease (config/<disease>), shared by the
  disease's 3 runs; external_data.csv is one item per org unit level (external_data/<fkt|csb>);
- R2 an item starts only when its prerequisites (inside its step) are in success;
- R3 one job at a time (enforced by the store);
- R4 a step is done when all its items are in success AND the previous step is done;
- R5 undoing a success needs confirm=true;
- R6 one forecast run (source x disease) open at a time (enforced by the store).
"""
from datetime import datetime

from etlhub.domain.exceptions import ConfirmationRequiredError, PipelineBlockedError

SOURCES = ("ADJ", "COM", "CSB")
DISEASES = ("Malaria", "Diarrhea", "Respinf")
COUPLES = [f"{s}/{d}" for s in SOURCES for d in DISEASES]
OU_LEVEL = {"ADJ": "6", "COM": "6", "CSB": "5"}
LEVEL = {"ADJ": "fkt", "COM": "fkt", "CSB": "csb"}  # external_data.csv: one file per org unit level

Rows = dict[tuple[str, str], dict]  # {(step, item): {"status", "job_id", "updated_at"}}; no row = pending


def run_context(couple: str) -> dict[str, str | None]:
    """Variables injected into every job of the run (like pivot_forecast.sh)."""
    source, disease = couple.split("/")
    return {
        "DISEASE_CODE": f"pridec_historic_{source}{disease}",
        "OU_LEVEL": OU_LEVEL[source],
        "ALERT_NAME": f"CSB{disease}Vigilance" if source == "CSB" else None,
    }


def disease_of(couple: str) -> str:
    return couple.split("/")[1]


def level_of(couple: str) -> str:
    return LEVEL[couple.split("/")[0]]


def config_item(couple: str) -> str:
    """config.json is uploaded once per disease, in the first run of that disease."""
    return f"config/{disease_of(couple)}"


def external_data_item(couple: str) -> str:
    """external_data.csv is uploaded once per org unit level, in the first run of that level."""
    return f"external_data/{level_of(couple)}"


def run_items(couple: str) -> dict[str, list[str]]:
    """The items of one forecast run and their prerequisites (the shared uploads are not listed here)."""
    c = couple
    items = {
        f"{c}:fetch_disease": [],
        f"{c}:fetch_climate": [],
        f"{c}:fetch_geojson": [],
        f"{c}:validate_inputs": [config_item(c), external_data_item(c),
                                 f"{c}:fetch_disease", f"{c}:fetch_climate", f"{c}:fetch_geojson"],
        f"{c}:forecast": [f"{c}:validate_inputs"],
    }
    last = f"{c}:forecast"
    if c.startswith("CSB/"):
        items[f"{c}:calc_orgunit_alerts"] = [last]
        last = f"{c}:calc_orgunit_alerts"
    items[f"{c}:approve"] = [last]  # human decision
    items[f"{c}:post_forecast"] = [f"{c}:approve"]
    return items


PIPELINE: dict[str, dict[str, list[str]]] = {  # step -> {item: prerequisites}, in cycle order
    "data_import": {
        "import_gee": [], "import_pivot_com": [], "import_pivot_csb": [],
        "approve_imports": ["import_pivot_com", "import_pivot_csb"],  # human decision: COM and CSB case counts
        "build_analytics": ["import_gee", "approve_imports"],
    },
    "forecast": {**{f"config/{d}": [] for d in DISEASES},  # 3 uploads, one per disease
                 **{f"external_data/{lv}": [] for lv in ("fkt", "csb")},  # + 2 uploads, one per level
                 **{k: v for c in COUPLES for k, v in run_items(c).items()}},  # + 66 run items = 71
    "system_update": {
        "build_analytics": [],
        "update_key": ["build_analytics"],
    },
}
RUN_TASKS = {"fetch_disease", "fetch_climate", "fetch_geojson", "validate_inputs", "forecast",
             "calc_orgunit_alerts", "post_forecast"}
STEPS = list(PIPELINE)


def this_month() -> str:
    return datetime.now().strftime("%Y%m")


def status(rows: Rows, step: str, item: str) -> str:
    return rows.get((step, item), {}).get("status", "pending")


def accessible_steps(rows: Rows) -> set[str]:
    """R4: a step is accessible when every step before it is done."""
    accessible, previous_done = set(), True
    for step, items in PIPELINE.items():
        if previous_done:
            accessible.add(step)
        previous_done = previous_done and all(status(rows, step, i) == "success" for i in items)
    return accessible


def run_scope(couple: str | None) -> set[str]:
    """What the open run may touch: its own items, its disease's config and its level's external_data."""
    return set(run_items(couple)) | {config_item(couple), external_data_item(couple)} if couple else set()


def blocking_reason(rows: Rows, step: str, item: str, open_couple: str | None = None) -> str | None:
    """Why (step, item) cannot start now (R2, R4, R6), or None when it can."""
    if step not in accessible_steps(rows):
        previous = STEPS[STEPS.index(step) - 1]
        return f"{item} needs step {previous} done first"
    if step == "forecast" and item not in run_scope(open_couple):
        return f"{item} needs its forecast run open (POST /pipeline/runs)"
    missing = [p for p in PIPELINE[step][item] if status(rows, step, p) != "success"]
    return f"{item} needs {step}/{missing[0]} in success first" if missing else None


def dependents(item: str) -> list[str]:
    """Items of the same run that depend on `item`, directly or not (forecast step only)."""
    items = PIPELINE["forecast"]
    found: list[str] = []
    frontier = [item]
    while frontier:
        current = frontier.pop()
        for candidate, prerequisites in items.items():
            if current in prerequisites and candidate not in found:
                found.append(candidate)
                frontier.append(candidate)
    return sorted(found, key=list(items).index)


def resolve_slot(task: str, rows: Rows, open_couple: str | None) -> tuple[str, str]:
    """The checkpoint (step, item) a launch counts for. Raises PipelineBlockedError.

    A run job counts for the open run. build_analytics has two slots: the first launchable one
    not in success, else the last launchable one (a relaunch, R5).
    """
    if task in RUN_TASKS:
        if open_couple is None:
            raise PipelineBlockedError(f"{task} needs an open forecast run (POST /pipeline/runs)")
        item = f"{open_couple}:{task}"
        if item not in PIPELINE["forecast"]:
            raise PipelineBlockedError(f"{task} is not part of run {open_couple}")
        candidates = [("forecast", item)]
    else:
        candidates = [(s, i) for s in STEPS for i in PIPELINE[s] if s != "forecast" and i == task]
        if not candidates:
            raise ValueError(f"{task} is not a pipeline job")
    ready = [c for c in candidates if blocking_reason(rows, *c, open_couple) is None]
    if not ready:
        raise PipelineBlockedError(blocking_reason(rows, *candidates[0], open_couple))
    return next((c for c in ready if status(rows, *c) != "success"), ready[-1])


def progress(rows: Rows, open_couple: str | None = None) -> dict:
    """Per-step state (done, accessible, items with launchable) and the current step. No writes."""
    steps, previous_done = [], True
    for step, items in PIPELINE.items():
        entries = [{"item": i, "status": "pending", "job_id": None, "updated_at": None, **rows.get((step, i), {}),
                    "launchable": blocking_reason(rows, step, i, open_couple) is None} for i in items]
        done = previous_done and all(e["status"] == "success" for e in entries)
        steps.append({"step": step, "done": done, "accessible": previous_done, "items": entries})
        previous_done = done
    current = next((s["step"] for s in steps if not s["done"]), None)  # None = cycle complete
    return {"current_step": current, "steps": steps}


def impact(step: str, item: str, rows: Rows, reset: list[str], stale_runs: list[str] | None = None) -> dict:
    """What undoing (step, item) costs: shown in the confirmation modal."""
    later = STEPS[STEPS.index(step) + 1:]
    kept = {s: sum(status(rows, s, i) == "success" for i in PIPELINE[s]) for s in later}
    result = {
        "item": item,
        "step": step,
        "current_step": progress(rows)["current_step"],
        "reset_items": [i for i in reset if (step, i) in rows],
        "blocked_steps": later,
        "kept_items": kept,
    }
    if stale_runs is not None:
        result["stale_runs"] = stale_runs  # other runs already computed with the previous file; they keep their success
    return result


def require_confirmation(step: str, item: str, rows: Rows, confirm: bool) -> None:
    """R5: relaunching an item in success needs confirm."""
    if confirm or status(rows, step, item) != "success":
        return
    raise ConfirmationRequiredError(f"{item} is already in success: resend with confirm=true to relaunch it",
                                    impact(step, item, rows, dependents(item)))


def require_input_confirmation(name: str, couple: str, rows: Rows, confirm: bool) -> list[str]:
    """R5 for config.json (per disease) and external_data.csv (per level) in the open run.

    Only the open run is reset (from validate_inputs on). Confirmation is needed once the open run's
    validate_inputs is in success, or once another run sharing the file has its forecast in success.
    Returns the items to reset.
    """
    shares = disease_of if name == "config" else level_of
    validate = f"{couple}:validate_inputs"
    reset = [validate, *[d for d in dependents(validate) if d.startswith(f"{couple}:")]]
    stale = [c for c in COUPLES if c != couple and shares(c) == shares(couple)
             and status(rows, "forecast", f"{c}:forecast") == "success"]
    if confirm or (status(rows, "forecast", validate) != "success" and not stale):
        return reset
    item = config_item(couple) if name == "config" else external_data_item(couple)
    raise ConfirmationRequiredError(
        f"{item} was already used: resend with confirm=true to replace it",
        impact("forecast", item, rows, reset, stale))
