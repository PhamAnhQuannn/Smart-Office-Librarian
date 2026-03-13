from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.connectors.github.validators import (
    ChunkLimitValidationError,
    FileSizeValidationError,
    FileSizeValidator,
)


def test_file_validator_accepts_files_up_to_1mb() -> None:
    validator = FileSizeValidator()

    validator.ensure_size_within_limit(size=1_000_000, path="docs/ok.md")


def test_file_validator_rejects_files_above_1mb() -> None:
    validator = FileSizeValidator()

    with pytest.raises(FileSizeValidationError, match="1MB"):
        validator.ensure_size_within_limit(size=1_000_001, path="docs/too-big.md")


def test_file_validator_accepts_chunk_counts_up_to_200() -> None:
    validator = FileSizeValidator()

    validator.ensure_chunk_count_within_limit(chunk_count=200, path="docs/ok.md")


def test_file_validator_rejects_chunk_counts_above_200() -> None:
    validator = FileSizeValidator()

    with pytest.raises(ChunkLimitValidationError, match="200 chunk"):
        validator.ensure_chunk_count_within_limit(chunk_count=201, path="docs/too-many.md")
