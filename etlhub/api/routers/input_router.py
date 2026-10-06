import csv

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from etlhub.application.use_cases.input_upload_service import InputName, InputUploadService
from etlhub.core.dependencies import get_input_upload_service
from etlhub.domain.exceptions import ValidationError

router = APIRouter(prefix="/input", tags=["Input Files"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _read_limited(file: UploadFile) -> bytes:
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"{file.filename} is larger than 10 MB")
    return content


@router.post(
    "/files/{name}",
    summary="Upload one forecast input file",
    description=(
        "Replaces input/config.json (name=config) or input/external_data.csv (name=external_data). "
        "Multipart field `file`, 10 MB max. Run /validate_inputs again afterwards: the forecast reads the *_valid files."
    ),
)
def upload_input_file(
    name: InputName,
    file: UploadFile = File(...),
    service: InputUploadService = Depends(get_input_upload_service),
) -> dict[str, str]:
    # Sync handler on purpose: FastAPI runs it in a threadpool, so file I/O does not block the loop.
    try:
        return {"saved": service.save(name, _read_limited(file))}
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/files",
    summary="Forecast input files on the server",
    description="Tells whether input/config.json and input/external_data.csv exist, with size and modification time.",
)
def input_files_status(
    service: InputUploadService = Depends(get_input_upload_service),
) -> dict[str, dict]:
    return service.status()


@router.delete(
    "/files/{name}",
    summary="Delete a forecast input file",
    description=(
        "Deletes input/config.json (name=config) or input/external_data.csv (name=external_data). "
        "Without config.json, /validate_inputs fails until a new upload."
    ),
)
def delete_input_file(
    name: InputName,
    service: InputUploadService = Depends(get_input_upload_service),
) -> dict[str, str]:
    try:
        return {"deleted": service.delete(name)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"{name} is not in input/") from exc


@router.get(
    "/files/config/preview",
    summary="Preview input/config.json",
    description="Returns the content of input/config.json. 422 when it is not a JSON object.",
)
def preview_config(
    service: InputUploadService = Depends(get_input_upload_service),
) -> dict:
    try:
        return service.preview_config()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="config is not in input/") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/files/external_data/preview",
    summary="Preview input/external_data.csv",
    description=(
        "First `limit` rows of input/external_data.csv, plus total_rows, period_range and org_units "
        "computed over the whole file."
    ),
)
def preview_external_data(
    limit: int = Query(100, ge=1, le=500),
    service: InputUploadService = Depends(get_input_upload_service),
) -> dict:
    try:
        return service.preview_external_data(limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="external_data is not in input/") from exc
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(status_code=422, detail=f"external_data.csv cannot be read: {exc}") from exc
