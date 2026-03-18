"""Domain model: Source (GitHub repo file metadata)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Source:
    id: str
    repo: str
    file_path: str
    source_url: str | None = None
    visibility: str = "private"  # "private" | "public"
    last_indexed_sha: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
