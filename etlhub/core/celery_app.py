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

# The forecast has its own queue: in production only its worker may run `docker run`.
celery_app.conf.update(task_track_started=True,
                       task_routes={"etlhub.infrastructure.tasks.task_forecast": {"queue": "forecast"}})
