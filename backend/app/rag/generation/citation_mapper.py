"""Maps retrieved source documents to citation references in an answer."""

from __future__ import annotations

from typing import Any


def map_citations(
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return citation objects for the top-3 sources.

    Each citation contains the keys expected by the API contract:
    file_path, source_url, start_line, end_line, score.
    """
    citations = []
    for source in sources[:3]:
        citations.append({
            "file_path": source.get("file_path", ""),
            "source_url": source.get("source_url"),
            "start_line": source.get("start_line"),
            "end_line": source.get("end_line"),
            "score": source.get("score", 0.0),
            "text": source.get("text", ""),
        })
    return citations
