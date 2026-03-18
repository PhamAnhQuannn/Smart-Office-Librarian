"""Text normalisation utilities for chunking."""

from __future__ import annotations

import re
import unicodedata


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into single spaces."""
    return re.sub(r"[\t ]+", " ", text).strip()


def normalize_unicode(text: str) -> str:
    """NFC-normalize Unicode and strip control characters."""
    text = unicodedata.normalize("NFC", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cc" or ch == "\n")


def strip_markdown_fences(text: str) -> str:
    """Remove triple-backtick code fences but keep their content."""
    return re.sub(r"^```[^\n]*\n", "", text, flags=re.MULTILINE)


def normalize_text(text: str) -> str:
    """Apply all normalisation steps in sequence."""
    text = normalize_unicode(text)
    text = normalize_whitespace(text)
    return text
