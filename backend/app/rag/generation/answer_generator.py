"""Calls the OpenAI chat API and collects streaming token events.

Returns a list of token strings that are emitted as SSE data events
by the query route.
"""

from __future__ import annotations

import logging
from typing import Any

from app.rag.generation.prompt_builder import build_messages

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Streams an LLM response using the OpenAI chat completions API."""

    def __init__(
        self,
        *,
        openai_client: Any,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> None:
        self._client = openai_client
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    def generate(
        self,
        query_text: str,
        sources: list[dict[str, Any]],
        *,
        max_context_chars: int = 8000,
    ) -> dict[str, Any]:
        """Call the LLM and return token_events + token usage counts.

        Returns a dict with keys:
            token_events  – list[str] of token strings
            prompt_tokens – int
            completion_tokens – int
        """
        messages = build_messages(query_text, sources, max_context_chars=max_context_chars)

        token_events: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0

        try:
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    token_events.append(delta.content)
                # Capture usage if provided on the final chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens or 0
                    completion_tokens = chunk.usage.completion_tokens or 0
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM generation failed: %s", exc)
            token_events = ["[Generation error — please retry]"]  # surface gracefully

        return {
            "token_events": token_events,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
