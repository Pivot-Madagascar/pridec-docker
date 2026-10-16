import os
import shutil
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from etlhub.api.routers import error_doc
from etlhub.core.config import get_settings

router = APIRouter(prefix="/output", tags=["Output Files"])


def _get_forecast_report_path() -> str:
    settings = get_settings()
    return os.path.join(settings.data_dir, "output", "forecast_report.html")


def _get_output_dir() -> str:
    settings = get_settings()
    return os.path.join(settings.data_dir, "output")


def _verify_signature() -> bool:
    """Verify that deletion is authorized via signature token."""
    settings = get_settings()
    sig_file = os.path.join(settings.data_dir, ".output_sig")
    
    if not os.path.exists(sig_file):
        return False
    
    try:
        with open(sig_file, 'r') as f:
            return len(f.read().strip()) > 0
    except Exception:
        return False


@router.delete(
    "/reset",
    summary="Delete output directory",
    description=(
        "Deletes the entire output directory and all its contents. Allowed only while `.output_sig` exists: "
        "a forecast run writes it, a successful reset removes it (403 otherwise)."
    ),
    responses={
        200: {"content": {"application/json": {"example": {"success": True, "message": "Output directory cleared"}}}},
        403: error_doc("No `.output_sig`: no forecast ran since the last reset",
                       {"detail": "Output directory deletion not authorized"}),
        500: error_doc("Some files could not be deleted", {"detail": "Failed to delete output directory: ..."}),
    },
)
def reset_output():
    # Plain `def`: FastAPI runs it in a thread, so deleting large files does not block the event loop.
    if not _verify_signature():
        raise HTTPException(
            status_code=403,
            detail="Output directory deletion not authorized"
        )

    output_dir = _get_output_dir()

    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
        except PermissionError:
            # No sudo fallback: forecast containers run as the etlhub user, so output/
            # is ours. Root-owned files come from runs made before that change.
            raise HTTPException(
                status_code=500,
                detail="Some files in output/ belong to another user (forecast run as root before). "
                       "Give them back to the etlhub user once: see GETTING_STARTED.md, 'output/ owned by root'.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete output directory: {str(e)}"
            )
        
        # Remove signature file after successful deletion
        sig_file = os.path.join(get_settings().data_dir, ".output_sig")
        try:
            if os.path.exists(sig_file):
                os.remove(sig_file)
        except Exception:
            pass

    return {"success": True, "message": "Output directory cleared"}


@router.get(
    "/forecast_report.html",
    response_class=HTMLResponse,
    summary="Get forecast report HTML",
    description="Returns the forecast report HTML file for approval.",
    responses={
        404: {
            "description": "Forecast report not found - run forecast step first",
        },
        500: error_doc("The file exists but cannot be read", {"detail": "Failed to read forecast report: ..."}),
    },
)
async def get_forecast_report():
    report_path = _get_forecast_report_path()

    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=404,
            detail="Forecast report not found. Run the forecast step first."
        )

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read forecast report: {str(e)}"
        )


@router.get(
    "/forecast_report.html/exists",
    response_model=dict,
    summary="Check if forecast report exists",
    description="Returns whether the forecast report HTML file exists.",
    responses={200: {"content": {"application/json": {"example": {"exists": True}}}}},
)
async def check_forecast_report_exists():
    report_path = _get_forecast_report_path()
    return {"exists": os.path.exists(report_path)}