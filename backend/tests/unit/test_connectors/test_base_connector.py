"""Unit tests for BaseConnector, ConnectorFile, and connector exceptions."""
from __future__ import annotations

import pytest

from app.connectors.base_connector import (
    BaseConnector,
    ConnectorError,
    ConnectorFile,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
)


# ── ConnectorFile ─────────────────────────────────────────────────────────────


class TestConnectorFile:
    def test_minimal_fields(self) -> None:
        f = ConnectorFile(path="docs/guide.md", content="# Guide", sha="abc123")
        assert f.path == "docs/guide.md"
        assert f.content == "# Guide"
        assert f.sha == "abc123"

    def test_optional_fields_defaults(self) -> None:
        f = ConnectorFile(path="f.md", content="text", sha="sha1")
        assert f.size == 0
        assert f.source_url is None
        assert f.metadata == {}

    def test_with_all_fields(self) -> None:
        f = ConnectorFile(
            path="src/main.py",
            content="print('hi')",
            sha="deadbeef",
            size=11,
            source_url="https://github.com/o/r/blob/main/src/main.py",
            metadata={"language": "python"},
        )
        assert f.size == 11
        assert f.metadata == {"language": "python"}


# ── BaseConnector (abstract) ──────────────────────────────────────────────────


class TestBaseConnector:
    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError):
            BaseConnector()  # type: ignore[abstract]

    def test_concrete_subclass_is_instantiable(self) -> None:
        class FakeConnector(BaseConnector):
            async def fetch_files(self, repo: str, branch: str = "main"):
                return []

            async def get_file(self, repo: str, path: str, branch: str = "main"):
                return ConnectorFile(path=path, content="", sha="0" * 40)

        connector = FakeConnector()
        assert connector is not None

    def test_subclass_missing_one_abstract_method_still_abstract(self) -> None:
        class IncompleteConnector(BaseConnector):
            async def fetch_files(self, repo: str, branch: str = "main"):
                return []
            # get_file not implemented

        with pytest.raises(TypeError):
            IncompleteConnector()  # type: ignore[abstract]


# ── Connector exceptions ──────────────────────────────────────────────────────


class TestConnectorExceptions:
    def test_connector_error_is_exception(self) -> None:
        err = ConnectorError("something failed")
        assert isinstance(err, Exception)

    def test_not_found_is_connector_error(self) -> None:
        err = ConnectorNotFoundError("file not found")
        assert isinstance(err, ConnectorError)

    def test_rate_limit_is_connector_error(self) -> None:
        err = ConnectorRateLimitError("rate limited")
        assert isinstance(err, ConnectorError)

    def test_raise_and_catch_hierarchy(self) -> None:
        with pytest.raises(ConnectorError):
            raise ConnectorNotFoundError("docs/missing.md not found")

    def test_error_message_preserved(self) -> None:
        err = ConnectorRateLimitError("429 Too Many Requests")
        assert "429" in str(err)
