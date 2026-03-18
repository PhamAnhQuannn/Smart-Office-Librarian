"""Celery application factory.

Broker and result backend are both Redis.  Tasks are auto-discovered from
the workers.tasks package.  Configure via environment variables:

    REDIS_URL          (default: redis://localhost:6379/0)
    CELERY_TASK_SOFT_TIME_LIMIT   (default: 300s)
    CELERY_TASK_TIME_LIMIT        (default: 600s)
"""

from __future__ import annotations

import os

from celery import Celery

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "embedlyzer",
    broker=_REDIS_URL,
    backend=_REDIS_URL,
    include=[
        "app.workers.tasks.ingest_tasks",
        "app.workers.tasks.backup_tasks",
        "app.workers.tasks.heartbeat_tasks",
        "app.workers.tasks.purge_tasks",
        "app.workers.tasks.reindex_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=int(
        os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "300")
    ),
    task_time_limit=int(
        os.environ.get("CELERY_TASK_TIME_LIMIT", "600")
    ),
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.ingest_tasks.*": {"queue": "ingest"},
        "app.workers.tasks.backup_tasks.*": {"queue": "maintenance"},
        "app.workers.tasks.purge_tasks.*": {"queue": "maintenance"},
        "app.workers.tasks.reindex_tasks.*": {"queue": "maintenance"},
        "app.workers.tasks.heartbeat_tasks.*": {"queue": "default"},
    },
    beat_schedule={
        "heartbeat-every-30s": {
            "task": "app.workers.tasks.heartbeat_tasks.heartbeat",
            "schedule": 30.0,
        },
    },
)
