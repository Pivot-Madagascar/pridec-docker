from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from etlhub.api.routers import BLOCKED, error_doc
from etlhub.application.use_cases import fetch_pivot
from etlhub.application.use_cases.analytics_service import AnalyticsService
from etlhub.application.use_cases.check_import_availability import COM_ELEMENTS, CSB_ELEMENTS
from etlhub.application.use_cases.ingestion_service import chosen_gee_variables, current_import_params
from etlhub.application.use_cases.journal_service import JournalService
from etlhub.api.auth.dhis2_auth import SESSION_COOKIE
from etlhub.core.dependencies import (get_analytics_service, get_auth_store, get_job_repository, get_journal_service,
                                      get_pipeline_gate, get_task_launcher)
from etlhub.core.job_context import current_test_mode
from etlhub.domain.interfaces.auth_store import AuthStore
from etlhub.domain.exceptions import ConfirmationRequiredError
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.interfaces.task_launcher import TaskLauncher

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

Source = Literal["ADJ", "COM", "CSB"]
Disease = Literal["Malaria", "Diarrhea", "Respinf"]
PASS = Query(None, pattern=r"^[0-9a-f]{8}$", description="A pass id; by default the pass the Dashboard shows")
PASS_PATH = Path(pattern=r"^[0-9a-f]{8}$", description="Pass id (one run of a cycle)", examples=["3f9c1a2b"])
CONFIRM = Query(False, description="Required to undo something already in success (409 confirmation_required otherwise)")


class RunRequest(BaseModel):
    source: Source
    disease: Disease


class Decision(BaseModel):
    decision: Literal["approve", "reject"]


class ImportsDecision(Decision):
    elements: list[Literal[*COM_ELEMENTS, *CSB_ELEMENTS]] | None = Field(
        None, description="approve: the fetched data elements to post (GET /pipeline/imports/fetched); [] posts nothing")


class Mode(BaseModel):
    test_mode: bool
    # What becomes of the active pass of the mode left (a pass lives in one mode); asked with a 409 when missing.
    pass_action: Literal["pause", "abandon"] | None = None


class PassStart(BaseModel):
    # Fixed for the pass (pass-config.md). The variables import_gee imports (GET /api/config gee_variables lists them;
    # absent: all). No dry_run: the mode decides (DRYRUN = TEST MODE); a dry_run sent is ignored.
    gee_variables: list[str] | None = None


class Cycle(BaseModel):
    cycle: str | None = Field(None, pattern=r"^\d{4}(0[1-9]|1[0-2])$")


@router.get(
    "/checkpoints",
    summary="Where the pipeline cycle stands",
    description=(
        "Per step: done, accessible and its items (status pending, running, success, error, and launchable). "
        "`pass` is the pass shown (the active one, else the last one of the target month, null before its first "
        "launch): id, cycle, state (active, paused, complete, abandoned), started_at, started_by. "
        "`current_step` is the first step not done (null = complete), `run` the open forecast run, "
        "`lock` the running job. A launch that breaks a rule gets 409 and writes nothing."
    ),
)
def get_checkpoints(
    pass_id: str | None = PASS,
    gate: PipelineGate = Depends(get_pipeline_gate),
) -> dict:
    return gate.progress(pass_id)


@router.post(
    "/runs",
    status_code=201,
    summary="Open the forecast run of a source x disease",
    description=(
        "One run open at a time, step data_import done. Empties input/ and output/ and fixes DISEASE_CODE, "
        "OU_LEVEL and ALERT_NAME for every job of the run. Reopening a couple already closed in the cycle "
        "needs confirm=true and resets its items. The run closes when its post_forecast succeeds."
    ),
    responses={
        201: {"content": {"application/json": {"example": {
            "pass_id": "3f9c1a2b", "couple": "CSB/Malaria", "state": "open", "disease_code": "pridec_historic_CSBMalaria",
            "ou_level": "5", "alert_name": "CSBMalariaVigilance", "opened_at": "2026-10-16T09:00:00.000000",
        }}}},
        **BLOCKED,
    },
)
def open_run(body: RunRequest, confirm: bool = CONFIRM, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    return gate.open_run(f"{body.source}/{body.disease}", confirm)


@router.delete(
    "/runs/current",
    summary="Abandon the open forecast run",
    description="Nothing is published; the run's items go back to pending and the pass stays active. The couple "
                "reopens later from zero, without confirmation. Refused while a job runs.",
    responses=BLOCKED,
)
def abandon_run(gate: PipelineGate = Depends(get_pipeline_gate)) -> dict[str, str]:
    return {"abandoned": gate.abandon_run()}


@router.get(
    "/runs/{source}/{disease}/report",
    response_class=FileResponse,
    summary="Report of a closed forecast run",
    description="forecast_report.html as it was when the run closed (post_forecast success). 404 if none was kept.",
    responses={404: error_doc("No report kept for this run in the pass", {"detail": "No report kept for run CSB/Malaria"})},
)
def run_report(source: Source, disease: Disease, pass_id: str | None = PASS,
               gate: PipelineGate = Depends(get_pipeline_gate)) -> FileResponse:
    path = gate.report(pass_id, f"{source}/{disease}")
    if path is None:
        raise HTTPException(status_code=404, detail=f"No report kept for run {source}/{disease}")
    return FileResponse(path, media_type="text/html")


@router.post(
    "/runs/current/approve",
    summary="Approve or reject the open run's forecast",
    description=(
        "approve: the {couple}:approve checkpoint becomes success and unlocks post_forecast. "
        "reject: forecast and what follows go back to pending, to be redone."
    ),
    responses=BLOCKED,
)
def decide(body: Decision, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict[str, str]:
    return {"couple": gate.decide(body.decision), "decision": body.decision}


@router.post(
    "/runs/current/skip_alerts",
    summary="Skip calc_orgunit_alerts of the open CSB run (temporary)",
    description=(
        "{couple}:calc_orgunit_alerts becomes success without running anything, which unlocks approve. "
        "Temporary: no script implements calc_orgunit_alerts yet (POST /calc_orgunit_alerts answers 501)."
    ),
    responses=BLOCKED,
)
def skip_alerts(gate: PipelineGate = Depends(get_pipeline_gate)) -> dict[str, str]:
    return {"skipped": f"{gate.skip_alerts()}:calc_orgunit_alerts"}


@router.get(
    "/imports/fetched",
    summary="The Pivot data fetched in this pass, to approve element by element",
    description=(
        "Per Pivot import (import_pivot_com, import_pivot_csb), the data elements of its last fetch in the pass shown "
        "and the caller's mode (kept in Redis; empty when never fetched there): rows fetched and the value check (flagged: empty, missing or negative values, or above "
        "100 cases per fokontany (COM) / 500 per CSB, with its message), and `post`: null until the approval posts it, then {status: posted | empty | failed, at, dry_run, "
        "error} (reset by a new fetch of its import). Only the elements fetched are listed. Read only."
    ),
    responses={200: {"content": {"application/json": {"example": {"imports": [{"task": "import_pivot_com", "elements": [
        {"data_element": "pridec_historic_COMMalaria", "rows": 279, "flagged": False,
         "text": "numNA: 0 | minimum value: 0 | maximum value: 36 | negative values: 0 | number of values: 279",
         "error": None, "post": {"status": "posted", "at": "2026-11-23T15:40:12", "dry_run": True, "error": None}}]}]}}}}},
)
def fetched_imports() -> dict:
    return {"imports": fetch_pivot.fetched_imports()}


@router.post(
    "/imports/approve",
    summary="Approve the Pivot data elements to post, or reject the imports (step data_import)",
    description=(
        "approve, with `elements` (required, may be empty): the approve_imports job posts those fetched elements to "
        "DHIS2, synchronously, with the mode's DRYRUN (journal: launched with params {elements}); on success "
        "approve_imports is success and unlocks build_analytics. An element not fetched in this pass gets 409. "
        "Again after a success needs confirm=true. reject: approve_imports back to pending, nothing posted."
    ),
    responses={200: {"content": {"application/json": {"example": {"decision": "approve",
                                                                  "job_id": "approve_imports_1a2b3c4d"}}}},
               422: error_doc("approve without `elements`, or an unknown element", {"detail": "..."}),
               500: error_doc("A post failed", {"message": "approve_imports failed: ..."}), **BLOCKED},
)
# def, not async: the post runs in FastAPI's threadpool (as POST /post_forecast).
def decide_imports(body: ImportsDecision, confirm: bool = CONFIRM, gate: PipelineGate = Depends(get_pipeline_gate),
                   service: AnalyticsService = Depends(get_analytics_service)) -> dict[str, str]:
    if body.decision == "reject":
        gate.decide_imports("reject")
        return {"decision": "reject"}
    if body.elements is None:
        raise HTTPException(status_code=422, detail="approve needs `elements`: the data elements to post (may be empty)")
    return {"decision": "approve", "job_id": service.approve_imports(body.elements, confirm).job_id}


@router.put(
    "/mode",
    summary="Choose your mode (test or production)",
    description=(
        "The caller's mode, kept in their session: every later request of this session, and the jobs it launches, "
        "work in it; other users keep theirs. A session starts in test mode. test_mode=true: passes, runs, journal, "
        "requests and files kept apart from production (Redis, test/input, test/output); nothing of the other mode "
        "is readable. A pass lives in one mode: while the mode left has an active pass, 409 confirmation_required "
        "with `impact` {pass_id, cycle, mode, to, actions: [pause, abandon]} until `pass_action` says which; that pass "
        "is then paused or abandoned (journal: cause mode_change, reason 'Mode changed manually by the user'), which "
        "is refused while a job runs. The same mode again changes nothing. The mode also decides DHIS2 writes "
        "(DRYRUN = TEST MODE): every job launched in test mode is a dry run, every job in production writes "
        "(dry_run in GET /pipeline/checkpoints)."
    ),
    responses={200: {"content": {"application/json": {"example": {"test_mode": True}}}},
               401: error_doc("The session is gone", {"detail": "Not authenticated"}), **BLOCKED},
)
def set_mode(body: Mode, request: Request, store: AuthStore = Depends(get_auth_store),
             gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    if body.test_mode != current_test_mode():
        gate.leave_mode(body.pass_action)  # ConfirmationRequiredError (409) while its pass is active and no choice
    if not store.set_session_mode(request.cookies.get(SESSION_COOKIE, ""), body.test_mode):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"test_mode": body.test_mode}


@router.put(
    "/cycle",
    summary="Choose the month the next pass starts on",
    description=(
        "cycle=YYYYMM: the first launch starts a pass on that month (a month whose last pass is complete needs "
        "confirm=true on that launch; one with a paused pass is resumed from the journal instead). "
        "null or the current month: follow the calendar month (the default); a pass that follows it is paused when "
        "the month changes. A future month, a running job or an active pass on another month gets 409. Kept per mode."
    ),
    responses={200: {"content": {"application/json": {"example": {"cycle": "202610"}}}}, **BLOCKED},
)
def set_cycle(body: Cycle, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    return gate.set_cycle(body.cycle)


@router.post(
    "/passes",
    status_code=201,
    summary="Start a new pass",
    description=(
        "Home, \"New pass\": starts a pass on the target month at once, from data_import, with its folders "
        "input/<cycle>/<pass>/ and output/<cycle>/<pass>/. The config and external_data of the month's previous pass "
        "(paused or complete) are carried over, and so are the imports done in the month with the same parameters. "
        "A month whose last pass is complete or paused needs confirm=true (409 confirmation_required, impact "
        "complete_pass or paused_pass; a paused pass stays paused). Refused while a job runs or a pass is active. "
        "Its configuration is fixed now, for all its jobs, and journaled with pass_started: body `gee_variables` (the "
        "GEE variables its import_gee imports; absent: all of them; empty or unknown: 400), PARENT_OU and LOG_LEVEL of "
        "the editable config, the DHIS2 URL of the last login. A launch from a session on another DHIS2 is refused "
        "(409). DRYRUN is the mode's (DRYRUN = TEST MODE), never chosen: `dry_run` in the answer says it."
    ),
    responses={201: {"content": {"application/json": {"example": {
        "id": "3f9c1a2b", "cycle": "202610", "state": "active", "started_at": "2026-10-27T09:00:00.000000",
        "started_by": "jdoe", "gee_variables": "pridec_climate_temperatureMean,pridec_climate_precipitation",
        "parent_ou": "ou_parent", "log_level": "INFO", "dry_run": True, "dhis_url": "https://dhis2.example.org"}}}},
        400: error_doc("No GEE variable, or an unknown one", {"message": "Unknown GEE variables: pridec_climate_x"}),
        **BLOCKED},
)
def start_pass(body: PassStart | None = None, confirm: bool = CONFIRM,
               gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    body = body or PassStart()
    chosen = chosen_gee_variables(body.gee_variables)
    return gate.start_pass(confirm, current_import_params(gee_variables=chosen), ",".join(chosen))


@router.post(
    "/passes/current/pause",
    summary="Pause the active pass",
    description=(
        "Stop for now, resume later: the pass keeps its checkpoints and its open forecast run. Launches are refused "
        "until a pass is active again: resume it from the journal (POST /pipeline/passes/{pass_id}/resume). "
        "Refused while a job runs."
    ),
    responses={200: {"content": {"application/json": {"example": {
        "id": "3f9c1a2b", "cycle": "202610", "state": "paused", "started_at": "2026-10-22T09:00:00.000000",
        "started_by": "jdoe"}}}}, **BLOCKED},
)
def pause(gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    return gate.pause()


@router.post(
    "/passes/{pass_id}/resume",
    summary="Resume a paused pass",
    description=(
        "The pass becomes active again and launches go to its month. Refused while a job runs, while another pass is "
        "active, for a pass that is not paused, and for a pass of the other mode (switch mode first). If another run "
        "emptied input/ and output/ meanwhile, its open forecast run starts again from its fetches."
    ),
    responses=BLOCKED,
)
def resume(pass_id: str = PASS_PATH, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    return gate.resume(pass_id)


@router.post(
    "/passes/{pass_id}/abandon",
    summary="Abandon a pass",
    description=(
        "For good: an abandoned pass cannot be resumed. Its open forecast run is abandoned; its checkpoints stay "
        "readable. The month can be run again: the next launch on it starts a new pass. Refused while a job runs and "
        "for a pass that is complete or already abandoned."
    ),
    responses=BLOCKED,
)
def abandon(pass_id: str = PASS_PATH, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    return gate.abandon(pass_id)


@router.delete(
    "/lock",
    summary="Free the pipeline lock",
    description=(
        "For a job whose worker was killed: frees the lock and marks its running checkpoint and its job record as error "
        "(the toast, the tracking and the logs then see its end). "
        "The lock never expires on its own. One lock for both modes: a job of the other mode can be released too, "
        "never named (job_id null, task 'a job of the other mode'). Returns the freed job_id, or null (nothing held, "
        "or a job of the other mode). The workers are asked first: while the job still runs (or when no worker "
        "answers), 409 confirmation_required with `impact` {job_id, task, active: true | null} until `confirm=true`."
    ),
    responses=BLOCKED,
)
def release_lock(confirm: bool = Query(False, description="Required while the job holding the lock may still run"),
                 gate: PipelineGate = Depends(get_pipeline_gate),
                 jobs: JobRepository = Depends(get_job_repository),
                 launcher: TaskLauncher = Depends(get_task_launcher)) -> dict[str, str | None]:
    held = gate.held_lock()
    if held is None:
        return {"released": None}
    job_id = held["job_id"]
    shown_id, task = (job_id, held["task"]) if held["own"] else (None, "a job of the other mode")
    shown = f"{task} ({job_id})" if held["own"] else "A job of the other mode"
    active = launcher.is_active(job_id)
    if active is not False and not confirm:
        why = f"{shown} is still running" if active else f"No worker answered: whether {shown} still runs is unknown"
        raise ConfirmationRequiredError(
            f"{why}. Releasing the lock lets another job start while it may still run: it is marked error, "
            "but it goes on and can still write to DHIS2 and to input/ and output/.",
            {"job_id": shown_id, "task": task, "active": active})
    released = gate.release_lock(job_id)
    job = jobs.get(released) if released else None
    # A worker that is not dead after all still overwrites this with its own end.
    if job and job.get("status") in ("pending", "running"):
        jobs.set(released, {**job, "status": "error", "message": "Lock released by a user (worker killed)"})
    return {"released": released if held["own"] else None}


@router.get(
    "/cycles",
    summary="Cycles and their passes",
    description=(
        "Every month with passes of the current mode (TEST_MODE), plus the target month, newest first: `cycle`, "
        "`target` (launches go to it) and `passes`, newest first: id, state (active, paused, complete, abandoned), "
        "started_at, started_by, `mode` (the current one: a mode never lists the other's passes), `events` and "
        "`last_at` (latest event, or null; both leave out mode_changed)."
    ),
)
def list_cycles(gate: PipelineGate = Depends(get_pipeline_gate)) -> list[dict]:
    return gate.cycles()


_JOURNAL_DESCRIPTION = (
    "Every change of the pass, oldest first: pass_started, launched, succeeded, failed, reset, uploaded, removed, "
    "decided, skipped, run_opened, run_closed, run_abandoned, lock_released, mode_changed, paused, resumed, abandoned, "
    "cycle_closed. Each event has its "
    "actor (DHIS2 username, `worker`, `system`), `mode` (`production`, or `test` while Redis keeps the test journal) and "
    "`request`: the HTTP request that caused it, or null. Only a pass of the current mode has events: a pass of the "
    "other mode reads as empty, like an unknown one. Refusals (409) are not events: see /api/tracking/requests. "
    "Not seen: the `pridec` command line, build_analytics launched from DHIS2."
)


@router.get(
    "/passes/{pass_id}/journal",
    summary="Journal of a pass",
    description=_JOURNAL_DESCRIPTION,
)
def get_journal(pass_id: str = PASS_PATH, service: JournalService = Depends(get_journal_service)) -> list[dict]:
    return service.events(pass_id)


@router.get(
    "/passes/{pass_id}/journal.csv",
    response_class=Response,
    summary="Journal of a pass, as CSV",
    description="The same events as the JSON journal, one line each.",
    responses={200: {"content": {"text/csv": {}}}},
)
def get_journal_csv(pass_id: str = PASS_PATH, service: JournalService = Depends(get_journal_service)) -> Response:
    return Response(service.csv(pass_id), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="journal_{pass_id}.csv"'})
