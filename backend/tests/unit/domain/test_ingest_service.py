from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.connectors.github.client import GitHubClient
from app.connectors.github.validators import ChunkLimitValidationError, FileSizeValidationError
from app.domain.services.ingest_service import IngestDocument, IngestService


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


class _Transport:
    def __init__(self, trees: dict[str, list[dict]], files: dict[tuple[str, str], dict]) -> None:
        self.trees = trees
        self.files = files
        self.fetch_count = 0

    def get_repo_tree(self, *, repo: str, ref: str, headers: dict[str, str]) -> dict:
        return {"tree": self.trees.get(ref, [])}

    def get_file_contents(self, *, repo: str, path: str, ref: str, headers: dict[str, str]) -> dict:
        self.fetch_count += 1
        return self.files[(ref, path)]


class _IndexStore:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.documents: list[IngestDocument] = []
        self.deleted_paths: list[str] = []

    def apply_changes(self, *, deleted_paths: list[str], documents: list[IngestDocument]) -> None:
        if self.should_fail:
            raise RuntimeError("index apply failed")
        self.deleted_paths = list(deleted_paths)
        self.documents = list(documents)


class _SourceCatalog:
    def __init__(self, last_indexed_sha: str | None = None) -> None:
        self.last_indexed_sha = last_indexed_sha
        self.apply_count = 0

    def get_last_indexed_sha(self, repo: str) -> str | None:
        return self.last_indexed_sha

    def apply_changes(self, *, repo: str, deleted_paths: list[str], last_indexed_sha: str) -> None:
        self.apply_count += 1
        self.last_indexed_sha = last_indexed_sha


class _JobQueue:
    def enqueue(self, *, repo: str, branch: str, requested_by: str) -> str:
        return "job-123"


def _build_service(
    *,
    trees: dict[str, list[dict]],
    files: dict[tuple[str, str], dict],
    last_indexed_sha: str | None = None,
    should_fail: bool = False,
    chunk_counter=None,
) -> tuple[IngestService, _Transport, _IndexStore, _SourceCatalog]:
    transport = _Transport(trees=trees, files=files)
    client = GitHubClient(transport, token="gh-token")
    index_store = _IndexStore(should_fail=should_fail)
    source_catalog = _SourceCatalog(last_indexed_sha=last_indexed_sha)
    service = IngestService(
        client=client,
        index_store=index_store,
        source_catalog=source_catalog,
        job_queue=_JobQueue(),
        chunk_counter=chunk_counter,
    )
    return service, transport, index_store, source_catalog


def test_ingest_service_queues_job() -> None:
    service, _, _, _ = _build_service(trees={}, files={})

    job_id = service.queue_job(repo="acme/docs", branch="main", requested_by="admin-1")

    assert job_id == "job-123"


def test_ingest_service_rejects_files_over_1mb_before_content_fetch() -> None:
    service, transport, _, _ = _build_service(
        trees={"sha-new": [{"path": "docs/big.md", "sha": "big", "size": 1_000_001}]},
        files={("sha-new", "docs/big.md"): {"sha": "big", "size": 1_000_001, "content": _b64("x")}},
    )

    with pytest.raises(FileSizeValidationError, match="1MB"):
        service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

    assert transport.fetch_count == 0


def test_ingest_service_rejects_files_over_200_chunks() -> None:
    service, _, _, _ = _build_service(
        trees={"sha-new": [{"path": "docs/big.md", "sha": "big", "size": 20}]},
        files={("sha-new", "docs/big.md"): {"sha": "big", "size": 20, "content": _b64("x")}},
        chunk_counter=lambda text: 201,
    )

    with pytest.raises(ChunkLimitValidationError, match="200 chunk"):
        service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")


def test_ingest_service_updates_source_metadata_only_after_success() -> None:
    service, _, _, source_catalog = _build_service(
        trees={"sha-new": [{"path": "docs/a.md", "sha": "a", "size": 20}]},
        files={("sha-new", "docs/a.md"): {"sha": "a", "size": 20, "content": _b64("content")}},
        last_indexed_sha="sha-old",
    )

    service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

    assert source_catalog.last_indexed_sha == "sha-new"
    assert source_catalog.apply_count == 1


def test_ingest_service_does_not_update_metadata_when_index_apply_fails() -> None:
    service, _, _, source_catalog = _build_service(
        trees={"sha-new": [{"path": "docs/a.md", "sha": "a", "size": 20}]},
        files={("sha-new", "docs/a.md"): {"sha": "a", "size": 20, "content": _b64("content")}},
        last_indexed_sha="sha-old",
        should_fail=True,
    )

    with pytest.raises(RuntimeError, match="index apply failed"):
        service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

    assert source_catalog.last_indexed_sha == "sha-old"
    assert source_catalog.apply_count == 0


def test_ingest_service_uses_stored_last_indexed_sha_for_incremental_sync() -> None:
    service, _, index_store, source_catalog = _build_service(
        trees={
            "sha-old": [{"path": "docs/remove.md", "sha": "old", "size": 20}],
            "sha-new": [{"path": "docs/add.md", "sha": "new", "size": 20}],
        },
        files={("sha-new", "docs/add.md"): {"sha": "new", "size": 20, "content": _b64("content")}},
        last_indexed_sha="sha-old",
    )

    result = service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

    assert result.purged_paths == ["docs/remove.md"]
    assert index_store.documents[0].file_path == "docs/add.md"
    assert source_catalog.last_indexed_sha == "sha-new"


def test_ingest_service_defaults_visibility_to_private() -> None:
    service, _, index_store, _ = _build_service(
        trees={"sha-new": [{"path": "docs/a.md", "sha": "a", "size": 20}]},
        files={("sha-new", "docs/a.md"): {"sha": "a", "size": 20, "content": _b64("content")}},
    )

    service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

    assert index_store.documents[0].visibility == "private"
