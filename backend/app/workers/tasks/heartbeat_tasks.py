"""Heartbeat task — emits a liveness ping every 30 s via Celery Beat."""

from __future__ import annotations

import datetime
import logging

logger = logging.getLogger(__name__)

try:
    from app.workers.celery_app import celery_app

    @celery_app.task(name="app.workers.tasks.heartbeat_tasks.heartbeat", bind=True, ignore_result=True)
    def heartbeat(self) -> None:  # type: ignore[override]
        """Writes a timestamped heartbeat log line so monitoring can confirm the worker is alive."""
        ts = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        logger.info("heartbeat", extra={"ts": ts, "worker": self.request.hostname})

except ImportError:
    pass  # Celery not installed in this environment
