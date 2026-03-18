"""Tests for the threshold tuning utility (backend/scripts/tune_threshold.py)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TUNE_SCRIPT = REPO_ROOT / "backend" / "scripts" / "tune_threshold.py"


def _run_script(
    script_path: Path,
    *args: str,
    expect_success: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success:
        assert result.returncode == 0, (
            f"Script failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _write_eval_report(tmp_path: Path, pass_rate: float, total: int = 5) -> Path:
    passed = round(pass_rate * total)
    report = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": pass_rate,
        "overall_status": "PASS" if pass_rate == 1.0 else "FAIL",
    }
    report_path = tmp_path / "eval_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


class TestTuneThresholdScript:
    def test_script_file_exists(self) -> None:
        assert TUNE_SCRIPT.exists(), f"tune_threshold.py not found at {TUNE_SCRIPT}"

    def test_dry_run_with_perfect_pass_rate_suggests_tighten(self, tmp_path: Path) -> None:
        report_path = _write_eval_report(tmp_path, pass_rate=1.0)
        result = _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(report_path),
            "--current-threshold", "0.70",
            "--dry-run",
        )
        assert "tighten" in result.stdout.lower()

    def test_dry_run_with_low_pass_rate_suggests_loosen(self, tmp_path: Path) -> None:
        report_path = _write_eval_report(tmp_path, pass_rate=0.60)
        result = _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(report_path),
            "--current-threshold", "0.70",
            "--dry-run",
        )
        assert "loosen" in result.stdout.lower()

    def test_dry_run_with_acceptable_pass_rate_suggests_keep(self, tmp_path: Path) -> None:
        report_path = _write_eval_report(tmp_path, pass_rate=0.88)
        result = _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(report_path),
            "--current-threshold", "0.70",
            "--dry-run",
        )
        assert "keep" in result.stdout.lower()

    def test_output_file_written_when_not_dry_run(self, tmp_path: Path) -> None:
        report_path = _write_eval_report(tmp_path, pass_rate=1.0)
        output_path = tmp_path / "recommendation.json"
        _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(report_path),
            "--current-threshold", "0.70",
            "--output", str(output_path),
        )
        assert output_path.exists(), "Recommendation file was not written"
        rec = json.loads(output_path.read_text(encoding="utf-8"))
        assert "recommended_threshold" in rec
        assert "action" in rec
        assert "pass_rate" in rec
        assert "reason" in rec

    def test_missing_eval_file_returns_nonzero(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        result = _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(missing),
            "--dry-run",
            expect_success=False,
        )
        assert result.returncode != 0

    def test_tighten_action_reduces_threshold(self, tmp_path: Path) -> None:
        report_path = _write_eval_report(tmp_path, pass_rate=0.98)
        output_path = tmp_path / "rec.json"
        _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(report_path),
            "--current-threshold", "0.70",
            "--output", str(output_path),
        )
        rec = json.loads(output_path.read_text(encoding="utf-8"))
        assert rec["action"] == "tighten"
        assert rec["recommended_threshold"] < rec["current_threshold"]

    def test_loosen_action_increases_threshold(self, tmp_path: Path) -> None:
        report_path = _write_eval_report(tmp_path, pass_rate=0.60)
        output_path = tmp_path / "rec.json"
        _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(report_path),
            "--current-threshold", "0.70",
            "--output", str(output_path),
        )
        rec = json.loads(output_path.read_text(encoding="utf-8"))
        assert rec["action"] == "loosen"
        assert rec["recommended_threshold"] > rec["current_threshold"]

    def test_threshold_does_not_exceed_bounds(self, tmp_path: Path) -> None:
        # Loosening at 1.0 should clamp to 1.0
        report_path = _write_eval_report(tmp_path, pass_rate=0.0)
        output_path = tmp_path / "rec.json"
        _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(report_path),
            "--current-threshold", "1.0",
            "--output", str(output_path),
        )
        rec = json.loads(output_path.read_text(encoding="utf-8"))
        assert rec["recommended_threshold"] <= 1.0

    def test_threshold_does_not_go_below_zero(self, tmp_path: Path) -> None:
        # Tightening at 0.0 should stay 0.0
        report_path = _write_eval_report(tmp_path, pass_rate=1.0)
        output_path = tmp_path / "rec.json"
        _run_script(
            TUNE_SCRIPT,
            "--eval-file", str(report_path),
            "--current-threshold", "0.0",
            "--output", str(output_path),
        )
        rec = json.loads(output_path.read_text(encoding="utf-8"))
        assert rec["recommended_threshold"] >= 0.0
