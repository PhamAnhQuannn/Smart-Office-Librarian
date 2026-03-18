"""Typed ID aliases for domain entity identifiers."""
from __future__ import annotations

from typing import NewType

UserId = NewType("UserId", str)
SourceId = NewType("SourceId", str)
ChunkId = NewType("ChunkId", str)
RunId = NewType("RunId", str)
QueryLogId = NewType("QueryLogId", str)
FeedbackId = NewType("FeedbackId", str)
