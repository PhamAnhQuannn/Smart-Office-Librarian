"""Domain model: IngestRun."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class IngestRun:
    id: str
    repo: str
    branch: str = "main"
    requested_by: str | None = None
    status: str = "queued"  # "queued" | "running" | "completed" | "failed"
    ingested_documents: int = 0
    purged_paths: int = 0
    skipped_duplicates: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
