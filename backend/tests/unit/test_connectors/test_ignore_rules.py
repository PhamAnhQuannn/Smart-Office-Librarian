from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.connectors.github.ignore_rules import IgnoreRules


def test_ignore_rules_load_librarianignore_patterns() -> None:
    rules = IgnoreRules.from_librarianignore("# comment\nsecret/**\n*.tmp\n")

    assert rules.is_ignored("secret/token.txt") is True
    assert rules.is_ignored("notes.tmp") is True
    assert rules.is_ignored("docs/guide.md") is False


def test_ignore_rules_apply_builtin_blacklist() -> None:
    rules = IgnoreRules()

    assert rules.is_ignored("LICENSE") is True
    assert rules.is_ignored("node_modules/react/index.js") is True
    assert rules.is_ignored("src/app.py") is False


def test_ignore_rules_support_gitignore_style_matching() -> None:
    rules = IgnoreRules(patterns=["docs/private/*", "*.bak"])

    assert rules.is_ignored("docs/private/roadmap.md") is True
    assert rules.is_ignored("archive.bak") is True
    assert rules.is_ignored("docs/public/roadmap.md") is False
