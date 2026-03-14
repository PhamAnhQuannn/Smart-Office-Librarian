from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.connectors.github.client import (
    GitHubClient,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubScopeError,
)


class _Transport:
    def __init__(self) -> None:
        self.last_headers: dict[str, str] | None = None
        self.tree_payload = {
            "tree": [
                {"path": "docs/README.md", "sha": "sha-1", "size": 12, "type": "blob"},
                {"path": "docs", "sha": "tree-1", "type": "tree"},
            ]
        }
        self.file_payload = {
            "sha": "sha-1",
            "size": 12,
            "content": "SGVsbG8=",
            "encoding": "base64",
        }

    def get_repo_tree(self, *, repo: str, ref: str, headers: dict[str, str]) -> dict:
        self.last_headers = headers
        return self.tree_payload

    def get_file_contents(self, *, repo: str, path: str, ref: str, headers: dict[str, str]) -> dict:
        self.last_headers = headers
        return self.file_payload


def test_github_client_repo_tree_fetch_returns_blob_entries_only() -> None:
    transport = _Transport()
    client = GitHubClient(transport, token="gh-token")

    entries = client.list_repo_tree(repo="acme/docs", ref="main")

    assert len(entries) == 1
    assert entries[0].path == "docs/README.md"
    assert entries[0].sha == "sha-1"


def test_github_client_file_content_fetch_returns_payload() -> None:
    transport = _Transport()
    client = GitHubClient(transport, token="gh-token")

    payload = client.get_file_payload(repo="acme/docs", path="docs/README.md", ref="main")

    assert payload.path == "docs/README.md"
    assert payload.sha == "sha-1"
    assert payload.content == "SGVsbG8="


def test_github_client_sends_scoped_bearer_token_auth() -> None:
    transport = _Transport()
    client = GitHubClient(transport, token="scoped-token")

    client.list_repo_tree(repo="acme/docs", ref="main")

    assert transport.last_headers is not None
    assert transport.last_headers["Authorization"] == "Bearer scoped-token"


def test_github_client_allows_read_scoped_token_for_allowed_repo() -> None:
    transport = _Transport()
    client = GitHubClient(
        transport,
        token="scoped-token",
        token_scopes=["repo:read"],
        allowed_repositories=["acme/docs"],
    )

    entries = client.list_repo_tree(repo="acme/docs", ref="main")

    assert len(entries) == 1


def test_github_client_rejects_missing_read_scope() -> None:
    transport = _Transport()
    client = GitHubClient(
        transport,
        token="scoped-token",
        token_scopes=["metadata:read"],
        allowed_repositories=["acme/docs"],
    )

    with pytest.raises(GitHubScopeError, match="required read scope"):
        client.list_repo_tree(repo="acme/docs", ref="main")


def test_github_client_rejects_over_privileged_scope() -> None:
    transport = _Transport()
    client = GitHubClient(
        transport,
        token="scoped-token",
        token_scopes=["repo:read", "admin:org"],
        allowed_repositories=["acme/docs"],
    )

    with pytest.raises(GitHubScopeError, match="over-privileged"):
        client.list_repo_tree(repo="acme/docs", ref="main")


def test_github_client_rejects_repo_outside_allowlist() -> None:
    transport = _Transport()
    client = GitHubClient(
        transport,
        token="scoped-token",
        token_scopes=["repo:read"],
        allowed_repositories=["acme/docs"],
    )

    with pytest.raises(GitHubScopeError, match="Repository access denied"):
        client.list_repo_tree(repo="acme/other", ref="main")


def test_github_client_maps_rate_limit_response() -> None:
    transport = _Transport()
    transport.tree_payload = {"status_code": 429}
    client = GitHubClient(transport, token="gh-token")

    with pytest.raises(GitHubRateLimitError, match="rate limit"):
        client.list_repo_tree(repo="acme/docs", ref="main")


def test_github_client_maps_not_found_response() -> None:
    transport = _Transport()
    transport.file_payload = {"status_code": 404}
    client = GitHubClient(transport, token="gh-token")

    with pytest.raises(GitHubNotFoundError, match="not found"):
        client.get_file_payload(repo="acme/docs", path="docs/missing.md", ref="main")
