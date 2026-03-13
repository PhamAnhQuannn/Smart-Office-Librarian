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


def test_index_safety_service_builds_vector_metadata_with_required_tags() -> None:
    service = IndexSafetyService()

    metadata = service.build_vector_metadata(
        model_id="text-embedding-3-small-v1",
        index_version=3,
        base_metadata={"file_path": "docs/guide.md"},
    )

    assert metadata["file_path"] == "docs/guide.md"
    assert metadata["model_id"] == "text-embedding-3-small-v1"
    assert metadata["index_version"] == 3


def test_index_safety_service_rejects_invalid_vector_metadata_inputs() -> None:
    service = IndexSafetyService()

    with pytest.raises(ValueError, match="model_id is required"):
        service.build_vector_metadata(model_id="", index_version=1)

    with pytest.raises(ValueError, match="index_version must be >= 1"):
        service.build_vector_metadata(model_id="text-embedding-3-small-v1", index_version=0)


def test_index_safety_service_validates_required_vector_metadata_tags() -> None:
    service = IndexSafetyService()

    service.ensure_vector_metadata_tags(
        {
            "model_id": "text-embedding-3-small-v1",
            "index_version": 1,
        }
    )

    with pytest.raises(ValueError, match="vector metadata missing model_id"):
        service.ensure_vector_metadata_tags({"index_version": 1})

    with pytest.raises(ValueError, match="vector metadata missing index_version"):
        service.ensure_vector_metadata_tags({"model_id": "text-embedding-3-small-v1"})
