import io
import os
import zipfile
from pathlib import Path

from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir


def _root() -> Path:
    """Parent of the mode's input/ and output/: test/ in test mode. Read at each call: the mode is the request's."""
    return work_dir(get_settings().data_dir, "input", current_test_mode()).parent


class WorkDirOutputFiles:
    """OutputFiles on the mode's work folders (work_dir)."""

    def report(self) -> str | None:
        path = _root() / "output" / "forecast_report.html"
        if not os.path.exists(path):  # os.path: False on any OSError, as before (Path.exists raises some)
            return None
        return path.read_text(encoding="utf-8")

    def archive(self, folder: str | None) -> bytes | None:
        root = _root()
        buffer = io.BytesIO()
        # ponytail: zip built in memory (a few MB per run); stream from a temp file if runs grow to hundreds of MB.
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in (folder,) if folder else ("input", "output"):
                for path in sorted((root / name).rglob("*")):
                    top = path.relative_to(root / name).parts[0]
                    if len(top) == 6 and top.isdigit():  # input/<cycle>/, output/<cycle>/: the pass folders, not the open run
                        continue
                    if path.is_file() and not path.is_symlink():
                        archive.write(path, path.relative_to(root))
        return buffer.getvalue() if archive.namelist() else None
