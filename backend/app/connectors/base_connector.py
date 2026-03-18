"""Abstract base class for all data source connectors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class ConnectorFile:
    """A single file fetched by a connector."""

    path: str
    content: str
    sha: str | None = None
    size: int = 0
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """Common interface that all source connectors must implement.

    Connectors are responsible for fetching raw file content from an
    external source (e.g. GitHub, local filesystem, S3).  The ingest
    pipeline calls :meth:`fetch_files` and never reaches into connector
    internals.
    """

    @abstractmethod
    async def fetch_files(
        self,
        *,
        repo: str,
        ref: str = "HEAD",
        path_filter: str | None = None,
    ) -> AsyncIterator[ConnectorFile]:
        """Yield files from the source one at a time.

        Args:
            repo: Source-specific repository/bucket identifier.
            ref:  Branch name, tag, or commit SHA (semantics depend on
                  the concrete connector implementation).
            path_filter: Optional glob pattern; connectors may use it to
                         reduce network I/O but callers must not rely on
                         it for correctness.

        Yields:
            :class:`ConnectorFile` instances in an unspecified order.
        """
        ...  # pragma: no cover

    @abstractmethod
    async def get_file(self, *, repo: str, path: str, ref: str = "HEAD") -> ConnectorFile:
        """Fetch a single file by path.

        Raises:
            ConnectorNotFoundError: If the file does not exist.
            ConnectorError: On any other retrieval failure.
        """
        ...  # pragma: no cover


class ConnectorError(Exception):
    """Base class for all connector failures."""


class ConnectorNotFoundError(ConnectorError):
    """Raised when the requested resource does not exist."""


class ConnectorRateLimitError(ConnectorError):
    """Raised when the upstream source signals rate-limiting."""
