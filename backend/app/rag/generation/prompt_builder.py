"""Constructs the system + user prompt for the LLM."""

from __future__ import annotations

from typing import Any

_SYSTEM_PROMPT = """\
You are Smart Office Librarian, an AI assistant that answers questions \
using only the provided source documents.

Rules:
- Base every answer strictly on the sources below.
- If the sources do not contain enough information, say so clearly.
- Always cite the source file path at the end of any claim.
- Be concise and accurate.
""".strip()


def build_messages(
    query_text: str,
    sources: list[dict[str, Any]],
    *,
    max_context_chars: int = 8000,
) -> list[dict[str, str]]:
    """Return the messages list expected by the OpenAI chat API."""
    context_parts: list[str] = []
    total_chars = 0

    for i, source in enumerate(sources, start=1):
        text = source.get("text", "")
        file_path = source.get("file_path", "unknown")
        entry = f"[{i}] {file_path}\n{text}"
        if total_chars + len(entry) > max_context_chars:
            break
        context_parts.append(entry)
        total_chars += len(entry)

    context_block = "\n\n---\n\n".join(context_parts) or "No relevant sources found."

    user_content = f"""Sources:\n{context_block}\n\nQuestion: {query_text}"""

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
