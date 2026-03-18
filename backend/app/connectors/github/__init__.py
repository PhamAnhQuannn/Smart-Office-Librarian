"""GitHub connector subpackage."""
from app.connectors.github.client import (
    GitHubClient,
    GitHubClientError,
    GitHubFilePayload,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubScopeError,
    GitHubTreeEntry,
)
from app.connectors.github.diff_scanner import GitDiffResult, GitDiffScanner, GitRename
from app.connectors.github.extractor import ExtractionError, GitHubExtractor
from app.connectors.github.ignore_rules import IgnoreRules
from app.connectors.github.validators import (
    ChunkLimitValidationError,
    FileSizeValidationError,
    FileSizeValidator,
)

__all__ = [
    "ChunkLimitValidationError",
    "ExtractionError",
    "FileSizeValidationError",
    "FileSizeValidator",
    "GitDiffResult",
    "GitDiffScanner",
    "GitHubClient",
    "GitHubClientError",
    "GitHubExtractor",
    "GitHubFilePayload",
    "GitHubNotFoundError",
    "GitHubRateLimitError",
    "GitHubScopeError",
    "GitHubTreeEntry",
    "GitRename",
    "IgnoreRules",
]
