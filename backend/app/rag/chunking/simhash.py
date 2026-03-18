"""SimHash-based near-duplicate detection for text chunks.

Produces a 64-bit hex fingerprint.  Two chunks with the same fingerprint
are considered identical for deduplication purposes.
"""

from __future__ import annotations

import hashlib
import re


def _tokenize(text: str) -> list[str]:
    """Return 3-gram tokens from normalised text."""
    normalised = re.sub(r"\s+", " ", text.lower().strip())
    return [normalised[i:i + 3] for i in range(len(normalised) - 2)]


def simhash(text: str) -> str:
    """Return a 64-bit hex fingerprint for *text*."""
    tokens = _tokenize(text)
    if not tokens:
        return "0" * 16

    # 64-bit vector of counts
    v = [0] * 64

    for token in tokens:
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= 1 << i

    return format(fingerprint, "016x")


def are_near_duplicates(fp1: str, fp2: str, *, max_hamming: int = 3) -> bool:
    """Return True if the Hamming distance between two fingerprints is ≤ max_hamming."""
    diff = int(fp1, 16) ^ int(fp2, 16)
    return bin(diff).count("1") <= max_hamming
