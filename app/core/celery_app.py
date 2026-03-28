from celery import Celery
from celery.schedules import crontab
from .config import settings

celery_app = Celery(
    "classtrack",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "analyze-attendance-nightly": {
            "task": "app.tasks.analyze_attendance_nightly",
            "schedule": crontab(hour=0, minute=0),  # Daily at midnight
        },
    },
)
