"""Backend stub: delegates to evaluation/scripts/evaluate_golden_questions.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_SCRIPT = REPO_ROOT / "evaluation" / "scripts" / "evaluate_golden_questions.py"


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(EVAL_SCRIPT), *sys.argv[1:]],
        cwd=REPO_ROOT,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
