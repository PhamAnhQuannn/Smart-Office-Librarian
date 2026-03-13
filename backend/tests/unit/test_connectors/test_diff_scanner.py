from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.connectors.github.client import GitHubTreeEntry
from app.connectors.github.diff_scanner import GitDiffScanner


def test_diff_scanner_detects_added_modified_and_deleted_files() -> None:
    scanner = GitDiffScanner()

    result = scanner.scan(
        previous_entries=[
            GitHubTreeEntry(path="docs/keep.md", sha="same"),
            GitHubTreeEntry(path="docs/change.md", sha="old"),
            GitHubTreeEntry(path="docs/remove.md", sha="gone"),
        ],
        current_entries=[
            GitHubTreeEntry(path="docs/keep.md", sha="same"),
            GitHubTreeEntry(path="docs/change.md", sha="new"),
            GitHubTreeEntry(path="docs/add.md", sha="add"),
        ],
    )

    assert [entry.path for entry in result.added] == ["docs/add.md"]
    assert [entry.path for entry in result.modified] == ["docs/change.md"]
    assert result.deleted == ["docs/remove.md"]


def test_diff_scanner_detects_rename_mapping_by_matching_sha() -> None:
    scanner = GitDiffScanner()

    result = scanner.scan(
        previous_entries=[GitHubTreeEntry(path="docs/old.md", sha="same-sha")],
        current_entries=[GitHubTreeEntry(path="docs/new.md", sha="same-sha")],
    )

    assert result.added == []
    assert result.deleted == []
    assert result.renamed[0].old_path == "docs/old.md"
    assert result.renamed[0].new_entry.path == "docs/new.md"


def test_diff_scanner_handles_empty_diff() -> None:
    scanner = GitDiffScanner()

    result = scanner.scan(previous_entries=[], current_entries=[])

    assert result.added == []
    assert result.modified == []
    assert result.deleted == []
    assert result.renamed == []
