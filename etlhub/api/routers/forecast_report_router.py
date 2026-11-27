import io
import logging
import os
import zipfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from etlhub.api.routers import error_doc
from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/output", tags=["Output Files"])


@router.get(
    "/forecast_report.html",
    response_class=HTMLResponse,
    summary="Get forecast report HTML",
    description="Returns the forecast report HTML file for approval.",
    responses={
        404: {
            "description": "Forecast report not found - run forecast step first",
        },
        500: error_doc("The file exists but cannot be read", {"detail": "Failed to read forecast report"}),
    },
)
def get_forecast_report():
    report_path = work_dir(get_settings().data_dir, "output", current_test_mode()) / "forecast_report.html"

    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=404,
            detail="Forecast report not found. Run the forecast step first."
        )

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except Exception:
        logger.exception("Failed to read forecast report %s", report_path)
        raise HTTPException(status_code=500, detail="Failed to read forecast report")


@router.get(
    "/archive",
    response_class=Response,
    summary="Download input/ and output/ as one zip",
    description="Zip of the open run's files, under `input/` and `output/`, to check the data or the forecast "
                "before approval. `folder=input`: only `input/`, the files the forecast will read (the run's "
                "Steps dialog, after the data check). Symbolic links are left out.",
    responses={
        200: {"content": {"application/zip": {}}},
        404: error_doc("input/ and output/ are both empty", {"detail": "No files in input/ or output/"}),
    },
)
def download_archive(
    folder: Literal["input", "output"] | None = Query(None, description="Only this folder; both when absent"),
):
    # Plain `def`: FastAPI runs it in a thread, so zipping does not block the event loop.
    root = work_dir(get_settings().data_dir, "input", current_test_mode()).parent  # the mode's: test/ in test mode
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
    if not archive.namelist():
        raise HTTPException(status_code=404, detail=f"No files in {folder or 'input/ or output'}/")
    filename = f"pridec_{folder}.zip" if folder else "pridec_input_output.zip"
    return Response(
        buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
