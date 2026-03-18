"""Backup tasks — triggered on a schedule or manually by admin API."""

from __future__ import annotations

import logging
import subprocess
import os

logger = logging.getLogger(__name__)

try:
    from app.workers.celery_app import celery_app
    from app.workers.retry_policy import BACKUP_RETRY_POLICY

    @celery_app.task(
        name="app.workers.tasks.backup_tasks.run_db_backup",
        bind=True,
        max_retries=BACKUP_RETRY_POLICY.max_retries,
        ignore_result=False,
    )
    def run_db_backup(self, *, label: str = "manual") -> dict:  # type: ignore[override]
        """Runs pg_dump via the backup_db.sh script and returns a summary dict."""
        script = os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "backup_db.sh")
        script = os.path.abspath(script)
        try:
            result = subprocess.run(
                ["bash", script],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"backup_db.sh exited {result.returncode}: {result.stderr[:500]}")
            logger.info("db_backup.completed", extra={"label": label})
            return {"status": "ok", "label": label, "stdout": result.stdout[-500:]}
        except Exception as exc:
            countdown = BACKUP_RETRY_POLICY.countdown_for_attempt(self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)

except ImportError:
    pass  # Celery not installed in this environment
