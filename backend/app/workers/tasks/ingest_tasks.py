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
		visibility: str = "private",
		job_id: str,
	) -> IngestTaskResult:
		result = self._ingest_service.sync_repository(
			repo=repo,
			current_commit_sha=current_commit_sha,
			previous_commit_sha=previous_commit_sha,
			librarianignore_text=librarianignore_text,
			visibility=visibility,
			job_id=job_id,
		)
		return IngestTaskResult(job_id=job_id, result=result)
