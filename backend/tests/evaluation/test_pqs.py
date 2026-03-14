"""Deterministic PQS runner/analyzer checks for the Step 66 NFR-1 gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_PQS_SCRIPT = REPO_ROOT / "evaluation" / "scripts" / "run_pqs.py"
ANALYZE_SCRIPT = REPO_ROOT / "evaluation" / "scripts" / "analyze_failures.py"


def _run_python_script(script_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Command failed: {sys.executable} {script_path} {' '.join(args)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result


def test_pqs_runner_and_analyzer_produce_pass_status(tmp_path: Path) -> None:
    summary_path = tmp_path / "pqs_summary.json"
    analysis_path = tmp_path / "pqs_analysis.json"

    _run_python_script(RUN_PQS_SCRIPT, "--output", str(summary_path))
    _run_python_script(
        ANALYZE_SCRIPT,
        "--input",
        str(summary_path),
        "--output",
        str(analysis_path),
    )

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    checks = analysis["checks"]

    assert analysis["overall_status"] == "PASS"
    assert {item["metric"] for item in checks} == {
        "e2e_p95_ms",
        "retrieval_p95_ms",
        "ttft_p95_ms",
    }
    assert all(item["status"] == "PASS" for item in checks)


def test_pqs_summary_shape_is_stable(tmp_path: Path) -> None:
    summary_path = tmp_path / "pqs_summary.json"

    _run_python_script(RUN_PQS_SCRIPT, "--output", str(summary_path))

    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["mode"] == "deterministic_baseline_scaffold"
    assert summary["generator"].endswith("evaluation/scripts/run_pqs.py")
    assert summary["profile_count"] == len(summary["profiles"])
    assert summary["profile_count"] >= 1
    assert set(summary["aggregate"]) == {
        "e2e_p95_ms",
        "retrieval_p95_ms",
        "ttft_p95_ms",
    }
