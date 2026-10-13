from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from etlhub.api.auth import require_admin
from etlhub.core.dependencies import get_pipeline_gate
from etlhub.domain.interfaces.pipeline_gate import PipelineGate

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

Source = Literal["ADJ", "COM", "CSB"]
Disease = Literal["Malaria", "Diarrhea", "Respinf"]
CYCLE = Query(None, pattern=r"^\d{6}$", description="YYYYMM; the current month by default")
CONFIRM = Query(False, description="Required to undo something already in success (409 confirmation_required otherwise)")


class RunRequest(BaseModel):
    source: Source
    disease: Disease


class Decision(BaseModel):
    decision: Literal["approve", "reject"]


class Mode(BaseModel):
    dry_run: bool


@router.get(
    "/checkpoints",
    summary="Where the pipeline cycle stands",
    description=(
        "Per step: done, accessible and its items (status pending, running, success, error, and launchable). "
        "`current_step` is the first step not done (null = cycle complete), `run` the open forecast run, "
        "`lock` the running job. A launch that breaks a rule gets 409 and writes nothing."
    ),
)
def get_checkpoints(
    cycle: str | None = CYCLE,
    gate: PipelineGate = Depends(get_pipeline_gate),
) -> dict:
    return gate.progress(cycle)


@router.post(
    "/runs",
    status_code=201,
    summary="Open the forecast run of a source x disease",
    description=(
        "One run open at a time, step data_import done. Empties input/ and output/ and fixes DISEASE_CODE, "
        "OU_LEVEL and ALERT_NAME for every job of the run. Reopening a couple already closed in the cycle "
        "needs confirm=true and resets its items. The run closes when its post_forecast succeeds."
    ),
)
def open_run(body: RunRequest, confirm: bool = CONFIRM, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    return gate.open_run(f"{body.source}/{body.disease}", confirm)


@router.delete(
    "/runs/current",
    summary="Abandon the open forecast run",
    description="Nothing is published; the run's items go back to pending. Administrators only (DHIS2 authority ALL).",
    dependencies=[Depends(require_admin)],
)
def abandon_run(gate: PipelineGate = Depends(get_pipeline_gate)) -> dict[str, str]:
    return {"abandoned": gate.abandon_run()}


@router.get(
    "/runs/{source}/{disease}/report",
    response_class=FileResponse,
    summary="Report of a closed forecast run",
    description="forecast_report.html as it was when the run closed (post_forecast success). 404 if none was kept.",
)
def run_report(source: Source, disease: Disease, cycle: str | None = CYCLE,
               gate: PipelineGate = Depends(get_pipeline_gate)) -> FileResponse:
    path = gate.report(cycle, f"{source}/{disease}")
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
)
def decide(body: Decision, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict[str, str]:
    return {"couple": gate.decide(body.decision), "decision": body.decision}


@router.post(
    "/imports/approve",
    summary="Approve or reject the imports (step data_import)",
    description=(
        "After import_pivot_com and import_pivot_csb, check the case counts (COM < 100, CSB < limit). "
        "approve: approve_imports becomes success and unlocks build_analytics. reject: back to pending."
    ),
)
def decide_imports(body: Decision, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict[str, str]:
    gate.decide_imports(body.decision)
    return {"decision": body.decision}


@router.put(
    "/mode",
    summary="Switch test mode (DRYRUN)",
    description=(
        "dry_run=true: the ETL scripts write nothing to DHIS2 (DRYRUN in the dynamic config) and the checkpoints are "
        "kept in Redis only. dry_run=false: back to production; the test checkpoints are discarded, which needs "
        "confirm=true when there are any. Refused while a job runs. GET /pipeline/checkpoints returns the mode."
    ),
)
def set_mode(body: Mode, confirm: bool = CONFIRM, gate: PipelineGate = Depends(get_pipeline_gate)) -> dict:
    return gate.set_mode(body.dry_run, confirm)


@router.delete(
    "/lock",
    summary="Free the pipeline lock",
    description=(
        "For a job whose worker was killed: frees the lock and marks its running checkpoint as error. "
        "The lock never expires on its own. Returns the freed job_id, or null. Administrators only (DHIS2 authority ALL)."
    ),
    dependencies=[Depends(require_admin)],
)
def release_lock(gate: PipelineGate = Depends(get_pipeline_gate)) -> dict[str, str | None]:
    return {"released": gate.release_lock()}
