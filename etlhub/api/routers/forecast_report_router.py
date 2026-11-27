import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from etlhub.api.routers import error_doc
from etlhub.core.dependencies import get_output_files
from etlhub.domain.interfaces.output_files import OutputFiles

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
def get_forecast_report(files: OutputFiles = Depends(get_output_files)):
    try:
        content = files.report()
    except Exception:
        logger.exception("Failed to read forecast report")
        raise HTTPException(status_code=500, detail="Failed to read forecast report")
    if content is None:
        raise HTTPException(
            status_code=404,
            detail="Forecast report not found. Run the forecast step first."
        )
    return HTMLResponse(content=content)


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
    files: OutputFiles = Depends(get_output_files),
):
    # Plain `def`: FastAPI runs it in a thread, so zipping does not block the event loop.
    content = files.archive(folder)
    if content is None:
        raise HTTPException(status_code=404, detail=f"No files in {folder or 'input/ or output'}/")
    filename = f"pridec_{folder}.zip" if folder else "pridec_input_output.zip"
    return Response(
        content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
