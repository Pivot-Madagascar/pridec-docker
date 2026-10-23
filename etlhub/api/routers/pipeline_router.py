from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from etlhub.api.auth import require_admin
from etlhub.api.routers import ADMIN_ONLY, BLOCKED, error_doc
from etlhub.application.use_cases.journal_service import JournalService
from etlhub.core.dependencies import get_job_repository, get_journal_service, get_pipeline_gate
from etlhub.domain.interfaces.job_repository import JobRepository
from etlhub.domain.interfaces.pipeline_gate import PipelineGate

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


class Mode(BaseModel):
    test_mode: bool


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
    description="Nothing is published; the run's items go back to pending. Administrators only (DHIS2 authority ALL).",
    dependencies=[Depends(require_admin)],
    responses={**BLOCKED, **ADMIN_ONLY},
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


@router.post(
    "/imports/approve",
    summary="Approve or reject the imports (step data_import)",
    description=(
        "After import_pivot_com and import_pivot_csb, check the case counts (COM < 100, CSB < limit). "
        "approve: approve_imports becomes success and unlocks build_analytics. reject: back to pending."
    ),
    responses=BLOCKED,
)
def decide_imports(body: Decision, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict[str, str]:
    gate.decide_imports(body.decision)
    return {"decision": body.decision}


@router.put(
    "/mode",
    summary="Switch test mode (TEST_MODE)",
    description=(
        "test_mode=true: the checkpoints, runs and uploads are kept apart from production (Redis only). "
        "test_mode=false: back to production; the active test pass is paused, its state kept in Redis to resume it "
        "in test mode. Refused while a job runs. DHIS2 writes are not switched here: they follow DRYRUN in the root .env, "
        "returned read-only as dry_run by GET /pipeline/checkpoints with test_mode."
    ),
    responses={200: {"content": {"application/json": {"example": {"test_mode": True}}}}, **BLOCKED},
)
def set_mode(body: Mode, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    return gate.set_mode(body.test_mode)


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
        "The lock never expires on its own. Returns the freed job_id, or null. Administrators only (DHIS2 authority ALL)."
    ),
    dependencies=[Depends(require_admin)],
    responses=ADMIN_ONLY,
)
def release_lock(gate: PipelineGate = Depends(get_pipeline_gate),
                 jobs: JobRepository = Depends(get_job_repository)) -> dict[str, str | None]:
    released = gate.release_lock()
    job = jobs.get(released) if released else None
    # A worker that is not dead after all still overwrites this with its own end.
    if job and job.get("status") in ("pending", "running"):
        jobs.set(released, {**job, "status": "error", "message": "Lock released by an administrator (worker killed)"})
    return {"released": released}


@router.get(
    "/cycles",
    summary="Cycles and their passes",
    description=(
        "Every month with passes, plus the target month, newest first: `cycle`, `target` (launches go to it) and "
        "`passes`, newest first: id, state (active, paused, complete, abandoned), started_at, started_by, `mode` "
        "(production, or test: kept in Redis only), `events` and `last_at` (latest event, or null; both leave out "
        "mode_changed)."
    ),
)
def list_cycles(gate: PipelineGate = Depends(get_pipeline_gate)) -> list[dict]:
    return gate.cycles()


_JOURNAL_DESCRIPTION = (
    "Every change of the pass, oldest first: pass_started, launched, succeeded, failed, reset, uploaded, removed, "
    "decided, skipped, run_opened, run_closed, run_abandoned, lock_released, mode_changed, paused, resumed, abandoned, "
    "cycle_closed. Each event has its "
    "actor (DHIS2 username, `worker`, `system`), `mode` (`production`, or `test` while Redis keeps the test journal) and "
    "`request`: the HTTP request that caused it, or null. Refusals (409) are not events: see /api/tracking/requests. "
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
    description="The same events as the JSON journal, one line each. Administrators only (DHIS2 authority ALL).",
    dependencies=[Depends(require_admin)],
    responses={200: {"content": {"text/csv": {}}}, **ADMIN_ONLY},
)
def get_journal_csv(pass_id: str = PASS_PATH, service: JournalService = Depends(get_journal_service)) -> Response:
    return Response(service.csv(pass_id), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="journal_{pass_id}.csv"'})
