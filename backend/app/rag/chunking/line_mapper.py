"""Maps character offsets in text to line numbers."""

from __future__ import annotations


def build_line_index(text: str) -> list[int]:
    """Return a list where element i is the char offset of line i+1."""
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def char_offset_to_line(offset: int, line_index: list[int]) -> int:
    """Return the 1-based line number for a character offset."""
    lo, hi = 0, len(line_index) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_index[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1  # 1-based
