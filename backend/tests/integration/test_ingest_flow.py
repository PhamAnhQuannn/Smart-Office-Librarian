"""FR-2 integration tests: ingestion lifecycle behavior."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from app.connectors.github.client import GitHubClient, GitHubFilePayload, GitHubTreeEntry
from app.domain.services.ingest_service import IngestDocument, IngestService
from app.workers.tasks.ingest_tasks import IngestTaskService


def _b64(text: str) -> str:
	return base64.b64encode(text.encode("utf-8")).decode("utf-8")


class _Transport:
	def __init__(self, trees: dict[str, list[dict]], files: dict[tuple[str, str], dict]) -> None:
		self._trees = trees
		self._files = files

	def get_repo_tree(self, *, repo: str, ref: str, headers: dict[str, str]) -> dict:
		return {"tree": self._trees.get(ref, [])}

	def get_file_contents(self, *, repo: str, path: str, ref: str, headers: dict[str, str]) -> dict:
		return self._files[(ref, path)]


class _IndexStore:
	def __init__(self, *, should_fail: bool = False) -> None:
		self.should_fail = should_fail
		self.deleted_paths: list[str] = []
		self.documents: list[IngestDocument] = []

	def apply_changes(self, *, deleted_paths: list[str], documents: list[IngestDocument]) -> None:
		if self.should_fail:
			raise RuntimeError("index apply failed")
		self.deleted_paths = list(deleted_paths)
		self.documents = list(documents)


class _SourceCatalog:
	def __init__(self, last_indexed_sha: str | None = None) -> None:
		self.last_indexed_sha = last_indexed_sha
		self.deleted_paths: list[str] = []

	def get_last_indexed_sha(self, repo: str) -> str | None:
		return self.last_indexed_sha

	def apply_changes(self, *, repo: str, deleted_paths: list[str], last_indexed_sha: str) -> None:
		self.deleted_paths = list(deleted_paths)
		self.last_indexed_sha = last_indexed_sha


def _service(
	*,
	trees: dict[str, list[dict]],
	files: dict[tuple[str, str], dict],
	last_indexed_sha: str | None = None,
	should_fail: bool = False,
) -> tuple[IngestService, _IndexStore, _SourceCatalog]:
	client = GitHubClient(_Transport(trees=trees, files=files), token="github-token")
	index_store = _IndexStore(should_fail=should_fail)
	source_catalog = _SourceCatalog(last_indexed_sha=last_indexed_sha)
	service = IngestService(client=client, index_store=index_store, source_catalog=source_catalog)
	return service, index_store, source_catalog


def test_ingest_flow_incremental_sync_ingests_new_and_purges_deleted() -> None:
	trees = {
		"sha-old": [
			{"path": "docs/keep.md", "sha": "keep-1", "size": 20},
			{"path": "docs/remove.md", "sha": "remove-1", "size": 20},
		],
		"sha-new": [
			{"path": "docs/keep.md", "sha": "keep-1", "size": 20},
			{"path": "docs/add.md", "sha": "add-1", "size": 20},
		],
	}
	files = {
		("sha-new", "docs/add.md"): {"sha": "add-1", "size": 20, "content": _b64("New document")},
	}
	service, index_store, source_catalog = _service(trees=trees, files=files, last_indexed_sha="sha-old")
	task_service = IngestTaskService(service)

	job_id = task_service.enqueue(repo="acme/docs", branch="main", requested_by="admin-1")
	result = task_service.run(repo="acme/docs", current_commit_sha="sha-new", job_id=job_id)

	assert result.job_id == job_id
	assert result.result.ingested_documents == 1
	assert index_store.deleted_paths == ["docs/remove.md"]
	assert index_store.documents[0].file_path == "docs/add.md"
	assert source_catalog.last_indexed_sha == "sha-new"


def test_ingest_flow_rename_detection_purges_old_path_and_ingests_new_path() -> None:
	trees = {
		"sha-old": [{"path": "docs/old.md", "sha": "same-sha", "size": 20}],
		"sha-new": [{"path": "docs/new.md", "sha": "same-sha", "size": 20}],
	}
	files = {
		("sha-new", "docs/new.md"): {"sha": "same-sha", "size": 20, "content": _b64("Renamed file")},
	}
	service, index_store, _ = _service(trees=trees, files=files, last_indexed_sha="sha-old")

	result = service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

	assert result.renamed_paths == [("docs/old.md", "docs/new.md")]
	assert index_store.deleted_paths == ["docs/old.md"]
	assert index_store.documents[0].file_path == "docs/new.md"


def test_ingest_flow_simhash_dedupe_skips_near_duplicate_content() -> None:
	trees = {
		"sha-new": [
			{"path": "docs/a.md", "sha": "a-1", "size": 20},
			{"path": "docs/b.md", "sha": "b-1", "size": 20},
		],
	}
	files = {
		("sha-new", "docs/a.md"): {"sha": "a-1", "size": 20, "content": _b64("Hello world")},
		("sha-new", "docs/b.md"): {"sha": "b-1", "size": 20, "content": _b64("hello   world")},
	}
	service, index_store, _ = _service(trees=trees, files=files)

	result = service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

	assert result.ingested_documents == 1
	assert result.skipped_duplicates == 1
	assert len(index_store.documents) == 1


def test_ingest_flow_updates_last_indexed_sha_only_after_success() -> None:
	trees = {"sha-new": [{"path": "docs/a.md", "sha": "a-1", "size": 20}]}
	files = {
		("sha-new", "docs/a.md"): {"sha": "a-1", "size": 20, "content": _b64("content")},
	}
	service, _, source_catalog = _service(trees=trees, files=files, last_indexed_sha="sha-old")

	service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

	assert source_catalog.last_indexed_sha == "sha-new"


def test_ingest_flow_failure_does_not_update_source_metadata() -> None:
	trees = {"sha-new": [{"path": "docs/a.md", "sha": "a-1", "size": 20}]}
	files = {
		("sha-new", "docs/a.md"): {"sha": "a-1", "size": 20, "content": _b64("content")},
	}
	service, _, source_catalog = _service(
		trees=trees,
		files=files,
		last_indexed_sha="sha-old",
		should_fail=True,
	)

	with pytest.raises(RuntimeError, match="index apply failed"):
		service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

	assert source_catalog.last_indexed_sha == "sha-old"


def test_ingest_flow_defaults_visibility_to_private() -> None:
	trees = {"sha-new": [{"path": "docs/private.md", "sha": "a-1", "size": 20}]}
	files = {
		("sha-new", "docs/private.md"): {"sha": "a-1", "size": 20, "content": _b64("private doc")},
	}
	service, index_store, _ = _service(trees=trees, files=files)

	service.sync_repository(repo="acme/docs", current_commit_sha="sha-new")

	assert index_store.documents[0].visibility == "private"
