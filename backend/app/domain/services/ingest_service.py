"""FR-2 ingestion orchestration.

Coordinates GitHub tree diffing, ignore rules, file validation, extraction,
deduplication, purge handling, and last_indexed_sha updates.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.connectors.github.client import GitHubClient, GitHubFilePayload, GitHubTreeEntry
from app.connectors.github.diff_scanner import GitDiffResult, GitDiffScanner
from app.connectors.github.extractor import GitHubExtractor
from app.connectors.github.ignore_rules import IgnoreRules
from app.connectors.github.validators import FileSizeValidator


@dataclass(frozen=True)
class IngestDocument:
	file_path: str
	text: str
	commit_sha: str
	visibility: str
	source_type: str = "github"


@dataclass(frozen=True)
class IngestSyncResult:
	job_id: str | None
	ingested_documents: int
	purged_paths: list[str]
	skipped_duplicates: int
	renamed_paths: list[tuple[str, str]]
	last_indexed_sha: str


class IngestIndexStore(Protocol):
	def apply_changes(self, *, deleted_paths: list[str], documents: list[IngestDocument]) -> None:
		...


class SourceCatalog(Protocol):
	def get_last_indexed_sha(self, repo: str) -> str | None:
		...

	def apply_changes(self, *, repo: str, deleted_paths: list[str], last_indexed_sha: str) -> None:
		...


class IngestJobQueue(Protocol):
	def enqueue(self, *, repo: str, branch: str, requested_by: str) -> str:
		...


class IngestService:
	"""Implements FR-2.1/2.2/2.3/2.4 for GitHub-backed ingestion."""

	_SUPPORTED_EXTENSIONS = {".md", ".txt", ".rst"}

	def __init__(
		self,
		*,
		client: GitHubClient,
		index_store: IngestIndexStore,
		source_catalog: SourceCatalog | None = None,
		job_queue: IngestJobQueue | None = None,
		diff_scanner: GitDiffScanner | None = None,
		extractor: GitHubExtractor | None = None,
		validator: FileSizeValidator | None = None,
		chunk_counter: callable | None = None,
	) -> None:
		self._client = client
		self._index_store = index_store
		self._source_catalog = source_catalog
		self._job_queue = job_queue
		self._diff_scanner = diff_scanner or GitDiffScanner()
		self._extractor = extractor or GitHubExtractor()
		self._validator = validator or FileSizeValidator()
		self._chunk_counter = chunk_counter or self._default_chunk_counter

	def queue_job(self, *, repo: str, branch: str, requested_by: str) -> str:
		if self._job_queue is not None:
			return self._job_queue.enqueue(repo=repo, branch=branch, requested_by=requested_by)
		return f"ingest-{uuid.uuid4()}"

	def sync_repository(
		self,
		*,
		repo: str,
		current_commit_sha: str,
		previous_commit_sha: str | None = None,
		librarianignore_text: str | None = None,
		visibility: str = "private",
		job_id: str | None = None,
	) -> IngestSyncResult:
		previous_sha = previous_commit_sha
		if previous_sha is None and self._source_catalog is not None:
			previous_sha = self._source_catalog.get_last_indexed_sha(repo)

		current_entries = self._client.list_repo_tree(repo=repo, ref=current_commit_sha)
		previous_entries = self._client.list_repo_tree(repo=repo, ref=previous_sha) if previous_sha else []

		diff = self._diff_scanner.scan(
			previous_entries=previous_entries,
			current_entries=current_entries,
		)
		ignore_rules = IgnoreRules.from_librarianignore(librarianignore_text)

		purged_paths = [path for path in diff.deleted if not ignore_rules.is_ignored(path)]
		renamed_paths: list[tuple[str, str]] = []
		candidate_entries: list[GitHubTreeEntry] = []

		for rename in diff.renamed:
			if ignore_rules.is_ignored(rename.old_path) and ignore_rules.is_ignored(rename.new_entry.path):
				continue
			purged_paths.append(rename.old_path)
			renamed_paths.append((rename.old_path, rename.new_entry.path))
			candidate_entries.append(rename.new_entry)

		for entry in [*diff.added, *diff.modified]:
			candidate_entries.append(entry)

		documents: list[IngestDocument] = []
		fingerprints: list[int] = []
		skipped_duplicates = 0

		for entry in candidate_entries:
			if ignore_rules.is_ignored(entry.path):
				continue
			if Path(entry.path).suffix.lower() not in self._SUPPORTED_EXTENSIONS:
				continue

			self._validator.ensure_size_within_limit(size=entry.size, path=entry.path)
			payload = self._client.get_file_payload(repo=repo, path=entry.path, ref=current_commit_sha)
			text = self._extractor.extract_text(payload)
			if text is None:
				continue

			chunk_count = self._chunk_counter(text)
			self._validator.ensure_chunk_count_within_limit(chunk_count=chunk_count, path=entry.path)

			fingerprint = self._simhash(self._normalize_text(text))
			if any(self._hamming_distance(fingerprint, seen) <= 3 for seen in fingerprints):
				skipped_duplicates += 1
				continue
			fingerprints.append(fingerprint)

			documents.append(
				IngestDocument(
					file_path=entry.path,
					text=text,
					commit_sha=current_commit_sha,
					visibility=visibility or "private",
				)
			)

		self._index_store.apply_changes(deleted_paths=purged_paths, documents=documents)

		if self._source_catalog is not None:
			self._source_catalog.apply_changes(
				repo=repo,
				deleted_paths=purged_paths,
				last_indexed_sha=current_commit_sha,
			)

		return IngestSyncResult(
			job_id=job_id,
			ingested_documents=len(documents),
			purged_paths=purged_paths,
			skipped_duplicates=skipped_duplicates,
			renamed_paths=renamed_paths,
			last_indexed_sha=current_commit_sha,
		)

	def _default_chunk_counter(self, text: str) -> int:
		if text == "":
			return 1
		return max(1, len(text.splitlines()))

	def _normalize_text(self, text: str) -> str:
		lowered = text.lower()
		return re.sub(r"\s+", " ", lowered).strip()

	def _simhash(self, text: str) -> int:
		if text == "":
			return 0

		weights = [0] * 64
		for token in text.split():
			digest = hashlib.sha256(token.encode("utf-8")).digest()[:8]
			hashed = int.from_bytes(digest, "big")
			for bit in range(64):
				weights[bit] += 1 if (hashed >> bit) & 1 else -1

		fingerprint = 0
		for bit, weight in enumerate(weights):
			if weight >= 0:
				fingerprint |= 1 << bit
		return fingerprint

	def _hamming_distance(self, left: int, right: int) -> int:
		return (left ^ right).bit_count()
