import csv
import io
import json

from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.interfaces.request_tracker import RequestTrackerProtocol

_CSV_COLUMNS = ("at", "mode", "cycle", "step", "item", "event", "actor", "job_id", "request_id",
                "method", "url", "status_code", "detail")


class JournalService:
    """The journal of a cycle: its pipeline events, each with the HTTP request that caused it (while it is kept)."""

    def __init__(self, gate: PipelineGate, request_tracker: RequestTrackerProtocol):
        self._gate = gate
        self._request_tracker = request_tracker

    def events(self, cycle: str) -> list[dict]:
        events = _job_outcomes(self._gate.journal(cycle))
        requests = self._request_tracker.get_many({e["request_id"] for e in events if e["request_id"]})
        return [{**e, "request": requests.get(e["request_id"])} for e in events]

    def csv(self, cycle: str) -> str:
        out = io.StringIO()
        writer = csv.DictWriter(out, _CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for e in self.events(cycle):
            writer.writerow({**(e["request"] or {}), **e, "detail": json.dumps(e["detail"]) if e["detail"] else None})
        return out.getvalue()


def _job_outcomes(events: list[dict]) -> list[dict]:
    """A job shows once, at its end: succeeded/failed take the actor, request and detail of its launched event.

    launched stays only for a job freed by DELETE /pipeline/lock (killed worker): it is the one trace of who launched it.
    A job still running does not show. Read side only: finish() needs the stored launched event.
    """
    launched = {e["job_id"]: e for e in events if e["event"] == "launched"}
    released = {e["job_id"] for e in events if e["event"] == "lock_released"}
    shown = []
    for e in events:
        start = launched.get(e["job_id"]) if e["event"] in ("succeeded", "failed") else None
        if start:
            e = {**e, "actor": start["actor"], "request_id": start["request_id"], "detail": e["detail"] or start["detail"]}
        if e["event"] != "launched" or e["job_id"] in released:
            shown.append(e)
    return shown
