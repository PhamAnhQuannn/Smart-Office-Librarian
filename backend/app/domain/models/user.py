"""Domain model: User."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    id: str
    email: str
    role: str  # "user" | "admin"
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    allowed_namespaces: list[str] = field(default_factory=list)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
