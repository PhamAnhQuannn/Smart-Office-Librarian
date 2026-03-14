"""Deterministic latency checks for the Step 66 NFR-1 evaluation gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_PQS_SCRIPT = REPO_ROOT / "evaluation" / "scripts" / "run_pqs.py"


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


def _assert_percentiles_in_order(metric: dict[str, float]) -> None:
    assert metric["p50"] <= metric["p95"] <= metric["p99"]


def test_latency_thresholds_match_nfr1_targets(tmp_path: Path) -> None:
    summary_path = tmp_path / "pqs_summary.json"

    _run_python_script(RUN_PQS_SCRIPT, "--output", str(summary_path))

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    profiles = summary["profiles"]
    aggregate = summary["aggregate"]

    assert profiles
    assert summary["profile_count"] == len(profiles)

    for profile in profiles:
        _assert_percentiles_in_order(profile["e2e_latency_ms"])
        _assert_percentiles_in_order(profile["retrieval_latency_ms"])
        _assert_percentiles_in_order(profile["ttft_ms"])

    assert aggregate["e2e_p95_ms"] <= 2000.0
    assert aggregate["retrieval_p95_ms"] <= 500.0
    assert aggregate["ttft_p95_ms"] <= 500.0


def test_latency_aggregate_is_max_profile_p95(tmp_path: Path) -> None:
    summary_path = tmp_path / "pqs_summary.json"

    _run_python_script(RUN_PQS_SCRIPT, "--output", str(summary_path))

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    profiles = summary["profiles"]
    aggregate = summary["aggregate"]

    assert aggregate["e2e_p95_ms"] == max(p["e2e_latency_ms"]["p95"] for p in profiles)
    assert aggregate["retrieval_p95_ms"] == max(
        p["retrieval_latency_ms"]["p95"] for p in profiles
    )
    assert aggregate["ttft_p95_ms"] == max(p["ttft_ms"]["p95"] for p in profiles)
