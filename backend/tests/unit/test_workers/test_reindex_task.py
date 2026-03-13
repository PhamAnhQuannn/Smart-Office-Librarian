from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.workers.tasks.reindex_tasks import (
    AtomicSwapError,
    ReindexTaskService,
    ReindexValidationError,
)


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


def test_reindex_finalize_swaps_namespace_when_validation_passes() -> None:
    store = _InMemoryPointerStore(active_namespace="dev-v1")
    service = ReindexTaskService(pointer_store=store)

    result = service.finalize_reindex(candidate_namespace="dev-v2", validation_passed=True)

    assert result.previous_namespace == "dev-v1"
    assert result.active_namespace == "dev-v2"
    assert result.swapped is True
    assert service.get_query_namespace() == "dev-v2"


def test_reindex_finalize_blocks_swap_on_validation_failure() -> None:
    store = _InMemoryPointerStore(active_namespace="dev-v1")
    service = ReindexTaskService(pointer_store=store)

    with pytest.raises(ReindexValidationError, match="failed validation"):
        service.finalize_reindex(candidate_namespace="dev-v2", validation_passed=False)

    # Old namespace remains live when validation fails.
    assert service.get_query_namespace() == "dev-v1"


def test_reindex_finalize_raises_when_atomic_swap_fails() -> None:
    store = _InMemoryPointerStore(active_namespace="dev-v1")
    service = ReindexTaskService(pointer_store=store)

    # Simulate external pointer update between read and compare-and-swap.
    original_cas = store.compare_and_swap_namespace

    def _racy_cas(*, expected_namespace: str, new_namespace: str) -> bool:
        store.active_namespace = "dev-v1-hotfix"
        return original_cas(expected_namespace=expected_namespace, new_namespace=new_namespace)

    store.compare_and_swap_namespace = _racy_cas  # type: ignore[method-assign]

    with pytest.raises(AtomicSwapError, match="changed before swap"):
        service.finalize_reindex(candidate_namespace="dev-v2", validation_passed=True)

    assert service.get_query_namespace() == "dev-v1-hotfix"


def test_reindex_finalize_is_noop_when_candidate_matches_active() -> None:
    store = _InMemoryPointerStore(active_namespace="dev-v2")
    service = ReindexTaskService(pointer_store=store)

    result = service.finalize_reindex(candidate_namespace="dev-v2", validation_passed=True)

    assert result.previous_namespace == "dev-v2"
    assert result.active_namespace == "dev-v2"
    assert result.swapped is False
