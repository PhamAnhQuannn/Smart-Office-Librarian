"""FR-4 integration tests: reindex atomic swap + index safety contracts.

These tests exercise IndexSafetyService and ReindexTaskService together,
verifying that safety validation correctly gates namespace swaps.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.services.index_safety_service import (
    IndexSafetyMismatchError,
    IndexSafetyService,
)
from app.workers.tasks.reindex_tasks import (
    AtomicSwapError,
    ReindexTaskService,
    ReindexValidationError,
)


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


class _InMemoryPointerStore:
    def __init__(self, active_namespace: str) -> None:
        self.active_namespace = active_namespace

    def get_active_namespace(self) -> str:
        return self.active_namespace

    def compare_and_swap_namespace(self, *, expected_namespace: str, new_namespace: str) -> bool:
        if self.active_namespace != expected_namespace:
            return False
        self.active_namespace = new_namespace
        return True


def _make_services(active_namespace: str = "prod-v1") -> tuple[IndexSafetyService, ReindexTaskService]:
    safety = IndexSafetyService()
    store = _InMemoryPointerStore(active_namespace=active_namespace)
    reindex = ReindexTaskService(pointer_store=store)
    return safety, reindex


# ---------------------------------------------------------------------------
# Integration flow: safety check passes → swap succeeds
# ---------------------------------------------------------------------------


def test_reindex_swap_succeeds_when_safety_check_passes() -> None:
    """When model/version match, safety check passes and namespace swaps."""
    safety, reindex = _make_services("prod-v1")

    # FR-4.1: build candidate metadata with matching tags
    candidate_meta = safety.build_vector_metadata(
        model_id="text-embedding-3-small-v1",
        index_version=1,
    )
    # FR-4.2: validate compatibility — no exception expected
    safety.ensure_compatible(
        expected_model_id="text-embedding-3-small-v1",
        expected_index_version=1,
        received_model_id=candidate_meta["model_id"],
        received_index_version=candidate_meta["index_version"],
    )

    result = reindex.finalize_reindex(candidate_namespace="prod-v2", validation_passed=True)

    assert result.swapped is True
    assert result.previous_namespace == "prod-v1"
    assert result.active_namespace == "prod-v2"
    assert reindex.get_query_namespace() == "prod-v2"


# ---------------------------------------------------------------------------
# Integration flow: model mismatch → safety raises 409-equivalent, no swap
# ---------------------------------------------------------------------------


def test_reindex_blocked_by_model_mismatch_error() -> None:
    """EMBEDDING_MODEL_MISMATCH from safety check prevents swap."""
    safety, reindex = _make_services("prod-v1")

    with pytest.raises(IndexSafetyMismatchError) as exc_info:
        safety.ensure_compatible(
            expected_model_id="text-embedding-3-small-v1",
            expected_index_version=1,
            received_model_id="text-embedding-ada-002",
            received_index_version=1,
        )

    err = exc_info.value
    assert err.error_code == "EMBEDDING_MODEL_MISMATCH"
    payload = err.to_error_payload()
    assert payload["error_code"] == "EMBEDDING_MODEL_MISMATCH"
    assert payload["details"]["expected_model_id"] == "text-embedding-3-small-v1"
    assert payload["details"]["received_model_id"] == "text-embedding-ada-002"

    # Safety check raised — swap never called; namespace unchanged
    assert reindex.get_query_namespace() == "prod-v1"


# ---------------------------------------------------------------------------
# Integration flow: index version mismatch → safety raises, no swap
# ---------------------------------------------------------------------------


def test_reindex_blocked_by_version_mismatch_error() -> None:
    """INDEX_VERSION_MISMATCH from safety check prevents swap."""
    safety, reindex = _make_services("prod-v1")

    with pytest.raises(IndexSafetyMismatchError) as exc_info:
        safety.ensure_compatible(
            expected_model_id="text-embedding-3-small-v1",
            expected_index_version=1,
            received_model_id="text-embedding-3-small-v1",
            received_index_version=2,
        )

    err = exc_info.value
    assert err.error_code == "INDEX_VERSION_MISMATCH"
    payload = err.to_error_payload()
    assert payload["details"]["expected_index_version"] == 1
    assert payload["details"]["received_index_version"] == 2

    assert reindex.get_query_namespace() == "prod-v1"


# ---------------------------------------------------------------------------
# Integration flow: validation_passed=False → ReindexValidationError, no swap
# ---------------------------------------------------------------------------


def test_reindex_blocked_when_validation_failed() -> None:
    """finalize_reindex raises ReindexValidationError and preserves namespace."""
    _, reindex = _make_services("prod-v1")

    with pytest.raises(ReindexValidationError, match="failed validation"):
        reindex.finalize_reindex(candidate_namespace="prod-v2", validation_passed=False)

    assert reindex.get_query_namespace() == "prod-v1"


# ---------------------------------------------------------------------------
# Integration flow: concurrent pointer change → AtomicSwapError
# ---------------------------------------------------------------------------


def test_reindex_raises_atomic_swap_error_on_concurrent_update() -> None:
    """AtomicSwapError is raised and query namespace reflects the racing write."""
    safety, reindex = _make_services("prod-v1")

    # Safety check passes for v1
    safety.ensure_compatible(
        expected_model_id="text-embedding-3-small-v1",
        expected_index_version=1,
        received_model_id="text-embedding-3-small-v1",
        received_index_version=1,
    )

    # Simulate race: another process swaps namespace before our CAS executes
    store = reindex._pointer_store  # type: ignore[attr-defined]
    original_cas = store.compare_and_swap_namespace

    def _racy_cas(*, expected_namespace: str, new_namespace: str) -> bool:
        store.active_namespace = "prod-v1-hotfix"
        return original_cas(expected_namespace=expected_namespace, new_namespace=new_namespace)

    store.compare_and_swap_namespace = _racy_cas  # type: ignore[method-assign]

    with pytest.raises(AtomicSwapError, match="changed before swap"):
        reindex.finalize_reindex(candidate_namespace="prod-v2", validation_passed=True)

    assert reindex.get_query_namespace() == "prod-v1-hotfix"


# ---------------------------------------------------------------------------
# Integration flow: metadata tagging round-trip
# ---------------------------------------------------------------------------


def test_metadata_tagging_round_trip_passes_validation() -> None:
    """build_vector_metadata output satisfies ensure_vector_metadata_tags."""
    safety, _ = _make_services()

    meta = safety.build_vector_metadata(
        model_id="text-embedding-3-small-v1",
        index_version=1,
        base_metadata={"file_path": "README.md", "start_line": 1, "end_line": 20},
    )

    # Must not raise
    safety.ensure_vector_metadata_tags(meta)

    assert meta["model_id"] == "text-embedding-3-small-v1"
    assert meta["index_version"] == 1
    assert meta["file_path"] == "README.md"


def test_metadata_tagging_fails_when_model_id_missing() -> None:
    """ensure_vector_metadata_tags raises when model_id is absent."""
    safety, _ = _make_services()

    with pytest.raises(ValueError, match="model_id"):
        safety.ensure_vector_metadata_tags({"index_version": 1})


def test_metadata_tagging_fails_when_index_version_missing() -> None:
    """ensure_vector_metadata_tags raises when index_version is absent."""
    safety, _ = _make_services()

    with pytest.raises(ValueError, match="index_version"):
        safety.ensure_vector_metadata_tags({"model_id": "text-embedding-3-small-v1"})


# ---------------------------------------------------------------------------
# Integration flow: sequential swaps advance namespace correctly
# ---------------------------------------------------------------------------


def test_sequential_swaps_advance_namespace() -> None:
    """Multiple successful swaps chain correctly; query namespace always current."""
    safety, reindex = _make_services("prod-v1")

    for version in (2, 3, 4):
        candidate = f"prod-v{version}"
        safety.ensure_compatible(
            expected_model_id="text-embedding-3-small-v1",
            expected_index_version=1,
            received_model_id="text-embedding-3-small-v1",
            received_index_version=1,
        )
        result = reindex.finalize_reindex(candidate_namespace=candidate, validation_passed=True)
        assert result.swapped is True
        assert reindex.get_query_namespace() == candidate
