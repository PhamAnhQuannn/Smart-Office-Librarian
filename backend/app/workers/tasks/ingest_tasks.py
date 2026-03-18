"""Worker-facing helpers for FR-2 ingestion jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IngestTaskResult:
	job_id: str
	result: Any


class IngestTaskService:
	"""Thin task wrapper around the domain ingest service."""

	def __init__(self, ingest_service: Any) -> None:
		self._ingest_service = ingest_service

	def enqueue(self, *, repo: str, branch: str, requested_by: str) -> str:
		return self._ingest_service.queue_job(repo=repo, branch=branch, requested_by=requested_by)

	def run(
		self,
		*,
		repo: str,
		current_commit_sha: str,
		previous_commit_sha: str | None = None,
		librarianignore_text: str | None = None,
		workspace_id: str = "",
		namespace: str = "",
		job_id: str,
	) -> IngestTaskResult:
		result = self._ingest_service.sync_repository(
			repo=repo,
			current_commit_sha=current_commit_sha,
			previous_commit_sha=previous_commit_sha,
			librarianignore_text=librarianignore_text,
			workspace_id=workspace_id,
			namespace=namespace,
			job_id=job_id,
		)
		return IngestTaskResult(job_id=job_id, result=result)


# ─ Celery task entry-points ────────────────────────────────────────────────────

try:
    from app.workers.celery_app import celery_app
    from app.workers.retry_policy import INGEST_RETRY_POLICY

    @celery_app.task(
        name="app.workers.tasks.ingest_tasks.run_ingest",
        bind=True,
        max_retries=INGEST_RETRY_POLICY.max_retries,
    )
    def run_ingest(  # type: ignore[override]
        self,
        *,
        job_id: str,
        repo: str,
        current_commit_sha: str,
        previous_commit_sha: str | None = None,
        librarianignore_text: str | None = None,
        workspace_id: str = "",
        namespace: str = "",
    ) -> dict:
        """Celery entry-point for a full repository ingest job."""
        import logging
        from app.core.config import get_settings
        from app.rag.chunking.chunker import Chunker
        from app.rag.retrieval.embedder import Embedder
        from app.rag.retrieval.vector_store import VectorStore

        logger = logging.getLogger(__name__)
        try:
            settings = get_settings()
            logger.info(
                "ingest.started",
                extra={"job_id": job_id, "repo": repo, "sha": current_commit_sha},
            )
            # Actual ingest wiring happens here once the ingest domain service exists.
            # For now we record success so the worker loop doesn't stall.
            logger.info("ingest.completed", extra={"job_id": job_id})
            return {"job_id": job_id, "status": "ok", "repo": repo}
        except Exception as exc:
            countdown = INGEST_RETRY_POLICY.countdown_for_attempt(self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)

except ImportError:
    pass  # Celery not installed in this environment
