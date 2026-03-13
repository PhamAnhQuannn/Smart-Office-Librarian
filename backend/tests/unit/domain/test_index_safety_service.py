from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.services.index_safety_service import IndexSafetyMismatchError, IndexSafetyService


def test_index_safety_service_allows_matching_model_and_version() -> None:
    service = IndexSafetyService()

    service.ensure_compatible(
        expected_model_id="text-embedding-3-small-v1",
        expected_index_version=1,
        received_model_id="text-embedding-3-small-v1",
        received_index_version=1,
    )


def test_index_safety_service_raises_model_mismatch_with_canonical_code() -> None:
    service = IndexSafetyService()

    with pytest.raises(IndexSafetyMismatchError) as exc:
        service.ensure_compatible(
            expected_model_id="text-embedding-3-small-v1",
            expected_index_version=1,
            received_model_id="text-embedding-3-large-v1",
            received_index_version=1,
        )

    payload = exc.value.to_error_payload()
    assert exc.value.error_code == "EMBEDDING_MODEL_MISMATCH"
    assert payload["details"]["expected_model_id"] == "text-embedding-3-small-v1"
    assert payload["details"]["expected_index_version"] == 1
    assert payload["details"]["received_model_id"] == "text-embedding-3-large-v1"
    assert payload["details"]["received_index_version"] == 1


def test_index_safety_service_raises_index_mismatch_with_canonical_code() -> None:
    service = IndexSafetyService()

    with pytest.raises(IndexSafetyMismatchError) as exc:
        service.ensure_compatible(
            expected_model_id="text-embedding-3-small-v1",
            expected_index_version=1,
            received_model_id="text-embedding-3-small-v1",
            received_index_version=2,
        )

    payload = exc.value.to_error_payload()
    assert exc.value.error_code == "INDEX_VERSION_MISMATCH"
    assert payload["details"]["expected_model_id"] == "text-embedding-3-small-v1"
    assert payload["details"]["expected_index_version"] == 1
    assert payload["details"]["received_model_id"] == "text-embedding-3-small-v1"
    assert payload["details"]["received_index_version"] == 2
