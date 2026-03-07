"""Data models for the memory subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Memory:
    """A single retrieved vector memory record."""

    memory_id: str
    user_id: str
    memory_text: str
    timestamp: float
    category: str = "general"
    distance: float = 0.0  # similarity distance (lower = more similar)

    def __str__(self) -> str:
        return self.memory_text
