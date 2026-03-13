"""Ingestion validators for file size and chunk count limits."""

from __future__ import annotations


MAX_FILE_SIZE_BYTES = 1_000_000
MAX_CHUNKS_PER_FILE = 200


class FileSizeValidationError(ValueError):
	"""Raised when a candidate file exceeds the 1MB ingestion limit."""


class ChunkLimitValidationError(ValueError):
	"""Raised when chunking would exceed the per-file chunk budget."""


class FileSizeValidator:
	def ensure_size_within_limit(self, *, size: int, path: str) -> None:
		if size > MAX_FILE_SIZE_BYTES:
			raise FileSizeValidationError(f"file exceeds 1MB limit: {path}")

	def ensure_chunk_count_within_limit(self, *, chunk_count: int, path: str) -> None:
		if chunk_count > MAX_CHUNKS_PER_FILE:
			raise ChunkLimitValidationError(f"file exceeds 200 chunk limit: {path}")
