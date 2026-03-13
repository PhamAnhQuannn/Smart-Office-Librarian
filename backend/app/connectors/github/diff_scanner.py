"""Git tree diff scanner for FR-2 incremental sync."""

from __future__ import annotations

from dataclasses import dataclass

from app.connectors.github.client import GitHubTreeEntry


@dataclass(frozen=True)
class GitRename:
	old_path: str
	new_entry: GitHubTreeEntry


@dataclass(frozen=True)
class GitDiffResult:
	added: list[GitHubTreeEntry]
	modified: list[GitHubTreeEntry]
	deleted: list[str]
	renamed: list[GitRename]


class GitDiffScanner:
	"""Computes added/modified/deleted files and rename mappings."""

	def scan(
		self,
		*,
		previous_entries: list[GitHubTreeEntry],
		current_entries: list[GitHubTreeEntry],
	) -> GitDiffResult:
		previous_by_path = {entry.path: entry for entry in previous_entries}
		current_by_path = {entry.path: entry for entry in current_entries}

		added_paths = [path for path in current_by_path if path not in previous_by_path]
		deleted_paths = [path for path in previous_by_path if path not in current_by_path]
		modified = [
			current_by_path[path]
			for path in current_by_path
			if path in previous_by_path and current_by_path[path].sha != previous_by_path[path].sha
		]

		added = [current_by_path[path] for path in added_paths]
		renamed: list[GitRename] = []
		remaining_added: list[GitHubTreeEntry] = []
		remaining_deleted = list(deleted_paths)

		for added_entry in added:
			rename_source = next(
				(
					old_path
					for old_path in remaining_deleted
					if previous_by_path[old_path].sha == added_entry.sha
				),
				None,
			)
			if rename_source is None:
				remaining_added.append(added_entry)
				continue

			renamed.append(GitRename(old_path=rename_source, new_entry=added_entry))
			remaining_deleted.remove(rename_source)

		return GitDiffResult(
			added=remaining_added,
			modified=modified,
			deleted=remaining_deleted,
			renamed=renamed,
		)
