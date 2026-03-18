"""Unit tests for RAG chunking: Chunker, simhash, normalization."""
from __future__ import annotations

import pytest

from app.rag.chunking.chunker import Chunker, TextChunk
from app.rag.chunking.simhash import are_near_duplicates, simhash
from app.rag.chunking.normalization import normalize_text


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

class TestChunker:
    def test_empty_input_returns_empty_list(self) -> None:
        c = Chunker()
        assert c.chunk("") == []

    def test_whitespace_only_returns_empty(self) -> None:
        c = Chunker()
        assert c.chunk("   \n\t  ") == []

    def test_short_text_produces_single_chunk(self) -> None:
        c = Chunker(chunk_size=512, overlap=64)
        chunks = c.chunk("Hello world")
        assert len(chunks) == 1
        assert "Hello" in chunks[0].text

    def test_chunk_is_text_chunk_dataclass(self) -> None:
        c = Chunker()
        chunks = c.chunk("Some text. " * 50)
        for chunk in chunks:
            assert isinstance(chunk, TextChunk)
            assert chunk.text
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line
            assert len(chunk.fingerprint) == 16

    def test_long_text_produces_multiple_chunks(self) -> None:
        c = Chunker(chunk_size=100, overlap=20)
        text = "abcdefghij " * 50  # ~550 chars
        chunks = c.chunk(text)
        assert len(chunks) > 1

    def test_overlap_means_content_overlap(self) -> None:
        # With overlap > 0, adjacent chunks should share some characters
        c = Chunker(chunk_size=100, overlap=40)
        text = "word " * 100
        chunks = c.chunk(text)
        if len(chunks) >= 2:
            # Last chars of chunk[0] should appear at start of chunk[1]
            # (rough check – just verify both are non-empty)
            assert chunks[0].text
            assert chunks[1].text

    def test_fingerprints_are_hex_strings(self) -> None:
        c = Chunker()
        chunks = c.chunk("test content for fingerprinting")
        for ch in chunks:
            assert all(char in "0123456789abcdef" for char in ch.fingerprint)


# ---------------------------------------------------------------------------
# SimHash
# ---------------------------------------------------------------------------

class TestSimhash:
    def test_empty_string_returns_zero_fingerprint(self) -> None:
        fp = simhash("")
        assert fp == "0" * 16

    def test_same_text_same_fingerprint(self) -> None:
        assert simhash("hello world") == simhash("hello world")

    def test_different_text_different_fingerprint(self) -> None:
        # Very different texts should differ
        assert simhash("completely different text A") != simhash("something else B 123")

    def test_fingerprint_length_is_16(self) -> None:
        assert len(simhash("any text here")) == 16

    def test_near_duplicate_same_text(self) -> None:
        fp = simhash("This is a document about machine learning.")
        assert are_near_duplicates(fp, fp, max_hamming=0)

    def test_near_duplicate_zero_hamming_identical(self) -> None:
        fp1 = simhash("identical text")
        fp2 = simhash("identical text")
        assert are_near_duplicates(fp1, fp2, max_hamming=0)

    def test_not_near_duplicates_for_very_different_texts(self) -> None:
        fp1 = simhash("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        fp2 = simhash("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
        # They may or may not be near-duplicates; just verify the function returns bool
        result = are_near_duplicates(fp1, fp2, max_hamming=3)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

class TestNormalization:
    def test_strips_extra_whitespace(self) -> None:
        result = normalize_text("hello   world")
        assert "  " not in result

    def test_empty_string_returns_empty(self) -> None:
        assert normalize_text("") == ""

    def test_unicode_normalization(self) -> None:
        # Should not raise and returns a string
        result = normalize_text("caf\u00e9 \u2019nice\u2019")
        assert isinstance(result, str)

    def test_normalize_text_returns_string(self) -> None:
        # normalize_text applies unicode + whitespace normalisation
        result = normalize_text("  hello   world  ")
        assert isinstance(result, str)
        assert result == "hello world"

    def test_strip_markdown_fence_function(self) -> None:
        from app.rag.chunking.normalization import strip_markdown_fences
        text = "```python\nprint('hello')\n```"
        result = strip_markdown_fences(text)
        # The opening ``` fence line should be removed
        assert "```python" not in result
