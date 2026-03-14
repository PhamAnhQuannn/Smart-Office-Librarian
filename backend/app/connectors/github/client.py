"""GitHub connector primitives for FR-2 ingestion flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GitHubTreeEntry:
	path: str
	sha: str
	size: int = 0
	type: str = "blob"


@dataclass(frozen=True)
class GitHubFilePayload:
	path: str
	sha: str
	size: int
	content: str
	encoding: str = "base64"


class GitHubClientError(Exception):
	"""Base connector failure."""


class GitHubNotFoundError(GitHubClientError):
	"""Raised when GitHub returns a 404-equivalent response."""


class GitHubRateLimitError(GitHubClientError):
	"""Raised when GitHub signals a rate-limit response."""


class GitHubScopeError(GitHubClientError):
	"""Raised when token scope or repository access violates least-privilege policy."""


class GitHubTransport(Protocol):
	def get_repo_tree(self, *, repo: str, ref: str, headers: dict[str, str]) -> dict[str, Any]:
		...

	def get_file_contents(self, *, repo: str, path: str, ref: str, headers: dict[str, str]) -> dict[str, Any]:
		...


class GitHubClient:
	"""Thin adapter over an injected GitHub transport."""

	_ALLOWED_READ_SCOPES = frozenset({"repo", "repo:read", "contents:read"})
	_FORBIDDEN_SCOPES = frozenset({"repo:write", "contents:write", "admin:org", "delete_repo"})

	def __init__(
		self,
		transport: GitHubTransport,
		*,
		token: str,
		token_scopes: list[str] | tuple[str, ...] | None = None,
		allowed_repositories: list[str] | tuple[str, ...] | None = None,
	) -> None:
		self._transport = transport
		self._token = token
		self._token_scopes = self._normalize_values(token_scopes)
		self._allowed_repositories = self._normalize_values(allowed_repositories)

	def _normalize_values(self, values: list[str] | tuple[str, ...] | None) -> set[str] | None:
		if values is None:
			return None
		return {value.strip().lower() for value in values if value and value.strip()}

	def _headers(self) -> dict[str, str]:
		return {
			"Accept": "application/vnd.github+json",
			"Authorization": f"Bearer {self._token}",
		}

	def _raise_for_error_payload(self, payload: dict[str, Any]) -> None:
		status_code = payload.get("status_code")
		if status_code == 404:
			raise GitHubNotFoundError("GitHub resource not found")
		if status_code == 429:
			raise GitHubRateLimitError("GitHub rate limit exceeded")

	def _enforce_least_privilege(self, *, repo: str) -> None:
		if self._allowed_repositories is not None and repo.lower() not in self._allowed_repositories:
			raise GitHubScopeError(f"Repository access denied by least-privilege policy: {repo}")

		if self._token_scopes is None:
			return

		if self._token_scopes.isdisjoint(self._ALLOWED_READ_SCOPES):
			raise GitHubScopeError("Token is missing a required read scope")

		over_privileged_scopes = self._token_scopes.intersection(self._FORBIDDEN_SCOPES)
		if over_privileged_scopes:
			raise GitHubScopeError(
				"Token has over-privileged scopes: " + ", ".join(sorted(over_privileged_scopes))
			)

	def list_repo_tree(self, *, repo: str, ref: str) -> list[GitHubTreeEntry]:
		self._enforce_least_privilege(repo=repo)
		payload = self._transport.get_repo_tree(repo=repo, ref=ref, headers=self._headers())
		self._raise_for_error_payload(payload)

		entries: list[GitHubTreeEntry] = []
		for item in payload.get("tree", []):
			if item.get("type", "blob") != "blob":
				continue
			entries.append(
				GitHubTreeEntry(
					path=item["path"],
					sha=item["sha"],
					size=item.get("size", 0),
					type=item.get("type", "blob"),
				)
			)
		return entries

	def get_file_payload(self, *, repo: str, path: str, ref: str) -> GitHubFilePayload:
		self._enforce_least_privilege(repo=repo)
		payload = self._transport.get_file_contents(
			repo=repo,
			path=path,
			ref=ref,
			headers=self._headers(),
		)
		self._raise_for_error_payload(payload)

		return GitHubFilePayload(
			path=path,
			sha=payload["sha"],
			size=payload.get("size", 0),
			content=payload.get("content", ""),
			encoding=payload.get("encoding", "base64"),
		)
