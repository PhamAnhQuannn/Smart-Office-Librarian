"""Domain model: Chunk (text fragment stored in Pinecone + metadata in PG)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Chunk:
    id: str
    source_id: str
    vector_id: str
    text: str
    namespace: str = "dev"
    simhash: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    created_at: datetime | None = None
