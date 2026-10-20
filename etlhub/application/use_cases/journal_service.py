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
        events = self._gate.journal(cycle)
        requests = self._request_tracker.get_many({e["request_id"] for e in events if e["request_id"]})
        return [{**e, "request": requests.get(e["request_id"])} for e in events]

    def csv(self, cycle: str) -> str:
        out = io.StringIO()
        writer = csv.DictWriter(out, _CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for e in self.events(cycle):
            writer.writerow({**(e["request"] or {}), **e, "detail": json.dumps(e["detail"]) if e["detail"] else None})
        return out.getvalue()
