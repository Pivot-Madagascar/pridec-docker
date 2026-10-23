from typing import Annotated
from urllib.parse import urlparse

from fastapi import Query
from pydantic import AfterValidator

from etlhub.core.config import get_settings, split_csv

CONFIRM_RELAUNCH = Query(False, description="Required to relaunch an item already in success (409 confirmation_required otherwise)")
CONFIRM_OVERWRITE = Query(False, description="Required once a forecast of the cycle is in success: this job overwrites its input files (409 confirmation_required otherwise)")


def _allowed_webhook(url: str) -> str:
    """https to a host of WEBHOOK_ALLOWED_HOSTS only: the worker POSTs to it from the host network."""
    parsed = urlparse(url)
    allowed = {h.lower() for h in split_csv(get_settings().webhook_allowed_hosts)}
    if parsed.scheme != "https" or parsed.hostname not in allowed:  # hostname: lowercase or None
        raise ValueError("webhook_url must be https to a host of WEBHOOK_ALLOWED_HOSTS")
    return url


# Optional outside Annotated: FastAPI 0.136 drops the validator of Annotated[str | None, ...] on a Query.
WebhookUrl = Annotated[str, AfterValidator(_allowed_webhook)] | None


def error_doc(description: str, example: dict) -> dict:
    """OpenAPI `responses` entry for an error answer. HTTPException bodies are {detail}, domain errors {message}."""
    return {"description": description, "content": {"application/json": {"example": example}}}


NOT_AUTHENTICATED = {401: error_doc("No valid session: log in with POST /auth/login", {"detail": "Not authenticated"})}
ADMIN_ONLY = {403: error_doc("The user is not a DHIS2 superuser (authority ALL)", {"detail": "Administrators only"})}
BLOCKED = {409: {
    "description": (
        "Refused by the pipeline gate, nothing written: a job is running, a previous step is not done, "
        "no forecast run is open, or `confirm=true` is needed (`code: confirmation_required`, with `impact`)."
    ),
    "content": {"application/json": {"examples": {
        "blocked": {"value": {"message": "import_gee (data_import) is running since ...: one job at a time"}},
        "confirmation_required": {"value": {
            "code": "confirmation_required",
            "message": "import_gee is already in success: resend with confirm=true to relaunch it",
            "impact": {"item": "import_gee", "step": "data_import", "current_step": "forecast",
                       "reset_items": ["import_gee", "build_analytics"], "blocked_steps": ["forecast", "system_update"],
                       "kept_items": {"forecast": 0, "system_update": 0}},
        }},
    }}},
}}
