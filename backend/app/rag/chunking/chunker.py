"""Text chunker: splits document text into overlapping fixed-size windows.

Chunk size and overlap are configurable.  Each chunk carries start/end
line numbers computed via line_mapper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.rag.chunking.line_mapper import build_line_index, char_offset_to_line
from app.rag.chunking.normalization import normalize_text
from app.rag.chunking.simhash import simhash


@dataclass(frozen=True)
class TextChunk:
    text: str
    start_line: int
    end_line: int
    fingerprint: str


class Chunker:
    """Splits text into overlapping windows."""

    def __init__(
        self,
        *,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> None:
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(self, text: str) -> list[TextChunk]:
        """Return a list of TextChunk objects for *text*."""
        normalised = normalize_text(text)
        if not normalised:
            return []

        line_index = build_line_index(normalised)
        step = self._chunk_size - self._overlap
        chunks: list[TextChunk] = []

        offset = 0
        while offset < len(normalised):
            end = min(offset + self._chunk_size, len(normalised))
            window = normalised[offset:end]
            # Snap to last newline to avoid mid-word splits when possible
            snap = window.rfind("\n")
            if snap > 0 and end < len(normalised):
                window = window[:snap]
                end = offset + snap

            start_line = char_offset_to_line(offset, line_index)
            end_line = char_offset_to_line(end - 1, line_index)
            fingerprint = simhash(window)

            chunks.append(
                TextChunk(
                    text=window.strip(),
                    start_line=start_line,
                    end_line=end_line,
                    fingerprint=fingerprint,
                )
            )

            offset += step
            if offset >= len(normalised):
                break

        return chunks
