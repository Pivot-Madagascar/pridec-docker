import csv
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from etlhub.domain.exceptions import ValidationError

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


def _write_atomic(path: Path, content: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(content)
    os.replace(tmp, path)


CHECKS = {"config": _check_config, "external_data": _check_external_data}


class InputUploadService:
    """Replaces the forecast input files after checking them."""

    def __init__(self, input_dir: Path):
        self.input_dir = Path(input_dir)

    def save(self, name: InputName, content: bytes) -> str:
        """Checks then replaces one input file. Raises ValidationError, leaving the old file in place."""
        CHECKS[name](content)
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

    def delete(self, name: InputName) -> str:
        """Raises FileNotFoundError when the file is not in input/."""
        file_name = FILE_NAMES[name]
        (self.input_dir / file_name).unlink()
        return f"input/{file_name}"

    def preview_config(self) -> dict:
        """Raises FileNotFoundError when absent, ValidationError when not a JSON object."""
        content = (self.input_dir / CONFIG_NAME).read_bytes()
        _check_config(content)
        return json.loads(content)

    def preview_external_data(self, limit: int) -> dict:
        """First `limit` rows plus a summary of the whole file, read line by line."""
        with open(self.input_dir / EXTERNAL_DATA_NAME, newline="", encoding="utf-8-sig") as f:
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
