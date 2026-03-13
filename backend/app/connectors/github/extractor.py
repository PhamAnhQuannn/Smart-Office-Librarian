"""Content extraction helpers for GitHub file payloads."""

from __future__ import annotations

import base64
import binascii

from app.connectors.github.client import GitHubFilePayload


class ExtractionError(Exception):
	"""Raised when a GitHub file payload cannot be decoded."""


class GitHubExtractor:
	"""Decodes base64 GitHub blob payloads to UTF-8 text."""

	def extract_text(self, payload: GitHubFilePayload) -> str | None:
		if payload.encoding != "base64":
			raise ExtractionError(f"unsupported encoding: {payload.encoding}")

		if payload.content == "":
			return ""

		try:
			normalized = payload.content.strip()
			padding = (-len(normalized)) % 4
			raw_bytes = base64.b64decode(
				normalized + ("=" * padding),
				altchars=b"-_",
				validate=True,
			)
		except (ValueError, binascii.Error) as exc:
			raise ExtractionError("invalid GitHub base64 payload") from exc

		if raw_bytes == b"":
			return ""

		try:
			return raw_bytes.decode("utf-8")
		except UnicodeDecodeError:
			return None
