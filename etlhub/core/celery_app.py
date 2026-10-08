from celery import Celery
from etlhub.core.config import get_settings

settings = get_settings()

redis_url = settings.redis_url

celery_app = Celery(
    "etlhub",
    broker=redis_url,
    backend=redis_url,
    include=["etlhub.infrastructure.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
