"""Domain model: BudgetStatus (token budget tracking)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BudgetStatus:
    monthly_budget: int
    tokens_used: int
    tokens_remaining: int
    is_exhausted: bool

    @classmethod
    def from_usage(cls, budget: int, used: int) -> "BudgetStatus":
        remaining = max(0, budget - used)
        return cls(
            monthly_budget=budget,
            tokens_used=used,
            tokens_remaining=remaining,
            is_exhausted=used >= budget,
        )
