"""Pagination types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    items: list[T] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20

    @property
    def has_next(self) -> bool:
        return (self.page * self.page_size) < self.total

    @property
    def has_prev(self) -> bool:
        return self.page > 1
