"""Ignore rules for ingestion candidate filtering."""

from __future__ import annotations

from fnmatch import fnmatch


class IgnoreRules:
	"""Applies builtin blacklist entries and .librarianignore patterns."""

	_BUILTIN_PATTERNS = [
		"LICENSE",
		"node_modules/",
		".git/",
		"__pycache__/",
		"*.pyc",
	]

	def __init__(self, patterns: list[str] | None = None) -> None:
		self._patterns = [*self._BUILTIN_PATTERNS, *(patterns or [])]

	@classmethod
	def from_librarianignore(cls, text: str | None) -> "IgnoreRules":
		patterns = []
		for line in (text or "").splitlines():
			candidate = line.strip()
			if not candidate or candidate.startswith("#"):
				continue
			patterns.append(candidate)
		return cls(patterns=patterns)

	def is_ignored(self, path: str) -> bool:
		normalized = path.replace("\\", "/").lstrip("./")
		for pattern in self._patterns:
			if self._matches(pattern, normalized):
				return True
		return False

	def _matches(self, pattern: str, path: str) -> bool:
		if pattern.endswith("/"):
			prefix = pattern[:-1]
			return path == prefix or path.startswith(pattern)
		if "/" not in pattern and fnmatch(path.split("/")[-1], pattern):
			return True
		return fnmatch(path, pattern)
