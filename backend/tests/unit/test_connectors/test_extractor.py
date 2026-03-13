from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.connectors.github.client import GitHubFilePayload
from app.connectors.github.extractor import ExtractionError, GitHubExtractor


def _payload(content: str, *, encoding: str = "base64") -> GitHubFilePayload:
    return GitHubFilePayload(path="docs/file.md", sha="sha-1", size=10, content=content, encoding=encoding)


def test_extractor_decodes_base64_utf8_text() -> None:
    extractor = GitHubExtractor()
    encoded = base64.b64encode("Hello world".encode("utf-8")).decode("utf-8")

    text = extractor.extract_text(_payload(encoded))

    assert text == "Hello world"


def test_extractor_skips_binary_payloads() -> None:
    extractor = GitHubExtractor()
    binary_bytes = bytes([0xFF, 0xFE, 0xFD])
    encoded = base64.b64encode(binary_bytes).decode("utf-8")

    text = extractor.extract_text(_payload(encoded))

    assert text is None


def test_extractor_handles_empty_payloads() -> None:
    extractor = GitHubExtractor()

    text = extractor.extract_text(_payload(""))

    assert text == ""


def test_extractor_maps_invalid_payloads_to_extraction_error() -> None:
    extractor = GitHubExtractor()

    with pytest.raises(ExtractionError, match="base64"):
        extractor.extract_text(_payload("***not-valid-base64***"))
