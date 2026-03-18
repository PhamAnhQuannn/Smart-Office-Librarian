"""Blue-green reindex helpers.

FR-4.3 requires building a candidate namespace in the background and only
atomically swapping the active pointer once validation succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


_POINTER_KEY = "embedlyzer:active_namespace"

# Lua script for atomic compare-and-swap on a Redis string key.
# Returns 1 if the swap was performed, 0 if the key held a different value.
_CAS_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if current == ARGV[1] then
    redis.call('SET', KEYS[1], ARGV[2])
    return 1
end
return 0
"""


class ReindexPointerStore(Protocol):
    """Abstraction for active namespace pointer persistence."""

    def get_active_namespace(self) -> str:
        ...

    def compare_and_swap_namespace(self, *, expected_namespace: str, new_namespace: str) -> bool:
        ...


class ReindexValidationError(Exception):
    """Raised when a candidate index fails validation and swap is blocked."""


class AtomicSwapError(Exception):
    """Raised when compare-and-swap fails because pointer state changed."""


class RedisPointerStore:
    """Redis-backed implementation of ReindexPointerStore.

    Stores the active Pinecone namespace as a plain Redis string key.
    ``compare_and_swap_namespace`` uses a Lua CAS script so the swap is
    atomic even with multiple Celery workers running.
    """

    def __init__(self, redis_client: Any, default_namespace: str = "dev") -> None:
        self._redis = redis_client
        self._default = default_namespace

    def get_active_namespace(self) -> str:
        value = self._redis.get(_POINTER_KEY)
        if value is None:
            return self._default
        return value.decode() if isinstance(value, bytes) else str(value)

    def compare_and_swap_namespace(
        self,
        *,
        expected_namespace: str,
        new_namespace: str,
    ) -> bool:
        result = self._redis.eval(
            _CAS_SCRIPT,
            1,             # number of KEYS
            _POINTER_KEY,  # KEYS[1]
            expected_namespace,  # ARGV[1]
            new_namespace,       # ARGV[2]
        )
        return bool(result)

@dataclass(frozen=True)
class ReindexSwapResult:
	previous_namespace: str
	active_namespace: str
	swapped: bool


class ReindexTaskService:
	"""Coordinates FR-4.3 blue-green namespace swaps."""

	def __init__(self, pointer_store: ReindexPointerStore) -> None:
		self._pointer_store = pointer_store

	def get_query_namespace(self) -> str:
		"""Queries should always resolve through the current active namespace."""
		return self._pointer_store.get_active_namespace()

	def finalize_reindex(self, *, candidate_namespace: str, validation_passed: bool) -> ReindexSwapResult:
		"""Finalizes reindex by atomically switching active namespace on success."""
		current_namespace = self._pointer_store.get_active_namespace()

		if not validation_passed:
			raise ReindexValidationError("candidate namespace failed validation")

		if candidate_namespace == current_namespace:
			return ReindexSwapResult(
				previous_namespace=current_namespace,
				active_namespace=current_namespace,
				swapped=False,
			)

		swapped = self._pointer_store.compare_and_swap_namespace(
			expected_namespace=current_namespace,
			new_namespace=candidate_namespace,
		)
		if not swapped:
			raise AtomicSwapError("active namespace changed before swap could complete")

		return ReindexSwapResult(
			previous_namespace=current_namespace,
			active_namespace=candidate_namespace,
			swapped=True,
		)

# ─ Celery task entry-points ────────────────────────────────────────────────────

try:
    from app.workers.celery_app import celery_app
    from app.workers.retry_policy import REINDEX_RETRY_POLICY

    @celery_app.task(
        name="app.workers.tasks.reindex_tasks.run_reindex_swap",
        bind=True,
        max_retries=REINDEX_RETRY_POLICY.max_retries,
    )
    def run_reindex_swap(  # type: ignore[override]
        self,
        *,
        candidate_namespace: str,
        validation_passed: bool = False,
    ) -> dict:
        """Atomically swaps the active Pinecone namespace to candidate after validation."""
        import logging

        import redis as redis_lib

        from app.core.config import get_settings

        logger = logging.getLogger(__name__)
        try:
            settings = get_settings()
            redis_client = redis_lib.from_url(settings.redis_url, decode_responses=False)
            pointer_store = RedisPointerStore(
                redis_client,
                default_namespace=settings.default_namespace,
            )
            service = ReindexTaskService(pointer_store)
            result = service.finalize_reindex(
                candidate_namespace=candidate_namespace,
                validation_passed=validation_passed,
            )
            logger.info(
                "reindex_swap.complete",
                extra={
                    "previous_namespace": result.previous_namespace,
                    "active_namespace": result.active_namespace,
                    "swapped": result.swapped,
                },
            )
            return {
                "status": "swapped" if result.swapped else "noop",
                "previous_namespace": result.previous_namespace,
                "active_namespace": result.active_namespace,
            }
        except (ReindexValidationError, AtomicSwapError) as exc:
            logger.error("reindex_swap.failed", extra={"error": str(exc)})
            raise
        except Exception as exc:
            countdown = REINDEX_RETRY_POLICY.countdown_for_attempt(self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)

except ImportError:
    pass  # Celery not installed in this environment