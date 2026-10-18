import csv
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from etlhub.domain.exceptions import PipelineBlockedError, ValidationError
from etlhub.domain.interfaces.default_files import DefaultFileSource
from etlhub.domain.interfaces.pipeline_gate import PipelineGate
from etlhub.domain.pipeline import config_item, external_data_item

CONFIG_NAME = "config.json"
EXTERNAL_DATA_NAME = "external_data.csv"
REQUIRED_CSV_COLUMNS = {"orgUnit", "period"}

InputName = Literal["config", "external_data"]
FILE_NAMES: dict[str, str] = {"config": CONFIG_NAME, "external_data": EXTERNAL_DATA_NAME}


def _check_config(content: bytes) -> None:
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{CONFIG_NAME} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{CONFIG_NAME} must be a JSON object")


def _check_external_data(content: bytes) -> None:
    try:
        header = next(csv.reader(io.StringIO(content.decode("utf-8-sig"))), [])
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValidationError(f"{EXTERNAL_DATA_NAME} is not a valid UTF-8 CSV: {exc}") from exc
    missing = REQUIRED_CSV_COLUMNS - {column.strip() for column in header}
    if missing:
        raise ValidationError(f"{EXTERNAL_DATA_NAME} is missing columns: {', '.join(sorted(missing))}")


def with_forecast_start(content: bytes, cycle: str) -> bytes:
    """config.json with forecast_start set to the cycle (YYYYMM), the default validate_inputs uses when absent.

    The cycle is the target one (PUT /pipeline/cycle, else the calendar month).
    ponytail: forecast_start = the cycle; switch to pivot_forecast.sh's value once confirmed (open point).
    """
    data = json.loads(content)
    data["forecast_start"] = cycle
    return json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8")


def _write_atomic(path: Path, content: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(content)
    os.replace(tmp, path)


CHECKS = {"config": _check_config, "external_data": _check_external_data}


class InputUploadService:
    """Replaces the forecast input files after checking them."""

    def __init__(self, input_dir: Path, gate: PipelineGate, defaults: DefaultFileSource | None = None):
        self.input_dir = Path(input_dir)
        self._gate = gate
        self._defaults = defaults

    def save(self, name: InputName, content: bytes, confirm: bool = False) -> str:
        """Checks then replaces one input file. Raises ValidationError, leaving the old file in place.

        Needs an open forecast run (PipelineBlockedError). config is the item config/<disease>: the server writes
        forecast_start into it (like jq in pivot_forecast.sh); external_data is the item external_data/<level>.
        After validate_inputs is in success, a change needs confirm (ConfirmationRequiredError).
        """
        CHECKS[name](content)
        if name == "config":
            content = with_forecast_start(content, self._gate.launch_cycle())
        with self._gate.change_input(name, confirm):
            self.input_dir.mkdir(parents=True, exist_ok=True)
            file_name = FILE_NAMES[name]
            _write_atomic(self.input_dir / file_name, content)
        return f"input/{file_name}"

    def status(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for name, file_name in FILE_NAMES.items():
            path = self.input_dir / file_name
            if not path.is_file():
                result[name] = {"exists": False}
                continue
            stat = path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
            result[name] = {"exists": True, "size": stat.st_size, "modified": modified}
        return result

    def delete(self, name: InputName, confirm: bool = False) -> str:
        """Raises FileNotFoundError when the file is not in input/. The checkpoint must be redone."""
        file_name = FILE_NAMES[name]
        with self._gate.change_input(name, confirm, removed=True):  # PipelineBlockedError without an open run
            (self.input_dir / file_name).unlink()
        return f"input/{file_name}"

    def _mode(self) -> str:
        return "test" if self._gate.progress()["dry_run"] else "production"

    def defaults(self) -> dict[str, dict]:
        """Default files of the current mode: item (config/<disease>, external_data/<level>) → {filename, size}."""
        return self._defaults.current(self._mode()) if self._defaults else {}

    def default_path(self, item: str) -> Path:
        """File of the default offered for item. Raises FileNotFoundError when there is none."""
        path = self._defaults.path(self._mode(), item) if self._defaults else None
        if path is None:
            raise FileNotFoundError(item)
        return path

    def save_default(self, name: InputName, confirm: bool = False) -> str:
        """Same as save, with the default file of the open run's item (config/<disease> or external_data/<level>).

        ponytail: the run is read before save checks it again; a run switched in between would get the other
        item's default (needs two people within milliseconds). Read the item inside change_input if that matters.
        """
        run = self._gate.progress()["run"]
        if run is None:
            raise PipelineBlockedError(f"Using the default {name} needs an open forecast run (POST /pipeline/runs)")
        item = config_item(run["couple"]) if name == "config" else external_data_item(run["couple"])
        return self.save(name, self.default_path(item).read_bytes(), confirm)

    def preview_config(self, path: Path | None = None) -> dict:
        """input/config.json, or the file at path. Raises FileNotFoundError when absent, ValidationError when not a JSON object."""
        content = (path or self.input_dir / CONFIG_NAME).read_bytes()
        _check_config(content)
        return json.loads(content)

    def preview_external_data(self, limit: int, path: Path | None = None) -> dict:
        """First `limit` rows plus a summary of the whole file (input/external_data.csv or path), read line by line."""
        with open(path or self.input_dir / EXTERNAL_DATA_NAME, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            columns = [column.strip() for column in next(reader, [])]
            org_index = columns.index("orgUnit") if "orgUnit" in columns else None
            period_index = columns.index("period") if "period" in columns else None
            rows: list[list[str]] = []
            total = 0
            org_units: set[str] = set()
            first_period: str | None = None
            last_period: str | None = None
            for row in reader:
                if not row:
                    continue
                total += 1
                if len(rows) < limit:
                    rows.append(row)
                if org_index is not None and org_index < len(row):
                    org_units.add(row[org_index])
                if period_index is not None and period_index < len(row) and row[period_index]:
                    # YYYYMM strings: lexical order is chronological order.
                    period = row[period_index]
                    first_period = min(first_period or period, period)
                    last_period = max(last_period or period, period)
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": total,
            "period_range": [first_period, last_period] if first_period else None,
            "org_units": len(org_units),
        }
