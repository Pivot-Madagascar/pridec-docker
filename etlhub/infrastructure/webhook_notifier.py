"""WebhookNotifier over HTTP (httpx): the job's end, POSTed by the worker (infrastructure/tasks.py)."""
import logging
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)


class HttpWebhookNotifier:
    def post(self, url: str, job_id: str, body: dict) -> None:
        try:
            # httpx does not follow redirects: the host checked at launch is the only one called.
            httpx.post(url, json=body, timeout=10)
        except Exception as e:  # the host only: the path or query of a webhook may carry a token
            logger.warning("Webhook of %s to %s failed: %s", job_id, urlsplit(url).hostname, type(e).__name__)
