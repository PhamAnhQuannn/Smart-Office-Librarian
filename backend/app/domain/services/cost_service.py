"""Cost service: token cost tracking and monthly budget enforcement.

Prices are sourced from OpenAI's published rates (2024):
  - text-embedding-3-small: $0.02 / 1M tokens
  - gpt-4o-mini prompt:     $0.15 / 1M tokens
  - gpt-4o-mini completion: $0.60 / 1M tokens
"""

from __future__ import annotations

from app.core.config import get_settings

# USD cost per token
_EMBEDDING_COST_PER_TOKEN = 0.02 / 1_000_000
_PROMPT_COST_PER_TOKEN = 0.15 / 1_000_000
_COMPLETION_COST_PER_TOKEN = 0.60 / 1_000_000


class CostService:
    """Tracks per-query token spend and enforces the monthly budget."""

    def __init__(self, *, monthly_token_budget: int | None = None) -> None:
        self._budget = monthly_token_budget or get_settings().monthly_token_budget
        self._tokens_used: int = 0  # in-memory accumulator (reset on restart)

    # ── cost calculation ───────────────────────────────────────────────────────────

    @staticmethod
    def estimate_query_cost(
        *,
        prompt_tokens: int,
        completion_tokens: int,
        embedding_tokens: int = 0,
    ) -> float:
        """Return estimated USD cost for a single query."""
        return (
            embedding_tokens * _EMBEDDING_COST_PER_TOKEN
            + prompt_tokens * _PROMPT_COST_PER_TOKEN
            + completion_tokens * _COMPLETION_COST_PER_TOKEN
        )

    # ── budget tracking ───────────────────────────────────────────────────────────

    def record_usage(self, *, tokens: int) -> None:
        """Accumulate token usage."""
        self._tokens_used += tokens

    def is_budget_exhausted(self) -> bool:
        """Return True when accumulated token usage exceeds monthly budget."""
        return self._tokens_used >= self._budget

    def remaining_tokens(self) -> int:
        return max(0, self._budget - self._tokens_used)

    def budget_status(self) -> dict:
        return {
            "budget": self._budget,
            "used": self._tokens_used,
            "remaining": self.remaining_tokens(),
            "exhausted": self.is_budget_exhausted(),
        }
