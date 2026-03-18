"""Tests for golden questions dataset validation (N-35)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EVAL_SCRIPT = REPO_ROOT / "evaluation" / "scripts" / "evaluate_golden_questions.py"
DATASET_PATH = REPO_ROOT / "evaluation" / "datasets" / "golden_questions_v1.json"


def _run_script(script_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Script failed: {sys.executable} {script_path} {' '.join(args)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result


class TestGoldenQuestionsDataset:
    def test_dataset_file_exists(self) -> None:
        assert DATASET_PATH.exists(), f"Dataset not found at {DATASET_PATH}"

    def test_dataset_is_non_empty_list(self) -> None:
        data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        assert isinstance(data, list), "Dataset must be a JSON array"
        assert len(data) > 0, "Dataset must have at least one golden question"

    def test_each_question_has_required_fields(self) -> None:
        required = {"id", "question", "expected_answer_keywords", "namespace", "min_confidence"}
        data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        for entry in data:
            missing = required - set(entry.keys())
            assert not missing, f"Entry {entry.get('id', '?')} missing fields: {missing}"

    def test_ids_are_unique(self) -> None:
        data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        ids = [entry["id"] for entry in data]
        assert len(ids) == len(set(ids)), "Duplicate IDs found in golden questions dataset"

    def test_confidence_levels_are_valid(self) -> None:
        valid = {"HIGH", "MEDIUM", "LOW"}
        data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        for entry in data:
            assert entry["min_confidence"] in valid, (
                f"Entry {entry['id']}: invalid min_confidence {entry['min_confidence']!r}"
            )

    def test_keywords_are_non_empty_lists(self) -> None:
        data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        for entry in data:
            kws = entry["expected_answer_keywords"]
            assert isinstance(kws, list) and len(kws) > 0, (
                f"Entry {entry['id']}: expected_answer_keywords must be a non-empty list"
            )

    def test_questions_are_non_empty_strings(self) -> None:
        data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        for entry in data:
            assert isinstance(entry["question"], str) and entry["question"].strip(), (
                f"Entry {entry['id']}: question must be a non-empty string"
            )

    def test_namespaces_are_strings(self) -> None:
        data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        for entry in data:
            assert isinstance(entry["namespace"], str) and entry["namespace"].strip(), (
                f"Entry {entry['id']}: namespace must be a non-empty string"
            )


class TestEvaluateGoldenQuestionsScript:
    def test_script_file_exists(self) -> None:
        assert EVAL_SCRIPT.exists(), f"Script not found at {EVAL_SCRIPT}"

    def test_script_produces_valid_json_report(self, tmp_path: Path) -> None:
        output_path = tmp_path / "report.json"
        _run_script(EVAL_SCRIPT, "--output", str(output_path))
        assert output_path.exists(), "Report file was not created"

        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert isinstance(report["total"], int)
        assert isinstance(report["passed"], int)
        assert isinstance(report["failed"], int)
        assert isinstance(report["pass_rate"], float)
        assert report["overall_status"] in {"PASS", "FAIL"}

    def test_all_golden_questions_pass_validation(self, tmp_path: Path) -> None:
        output_path = tmp_path / "report.json"
        _run_script(EVAL_SCRIPT, "--output", str(output_path))
        report = json.loads(output_path.read_text(encoding="utf-8"))
        failing = [r for r in report.get("results", []) if r["status"] != "PASS"]
        assert report["overall_status"] == "PASS", (
            f"{len(failing)} entries failed validation:\n"
            + "\n".join(f"  {r['id']}: {r['errors']}" for r in failing)
        )

    def test_report_total_matches_dataset(self, tmp_path: Path) -> None:
        dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        output_path = tmp_path / "report.json"
        _run_script(EVAL_SCRIPT, "--output", str(output_path))
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["total"] == len(dataset), (
            f"Report total {report['total']} != dataset length {len(dataset)}"
        )

    def test_report_pass_rate_is_one_for_valid_dataset(self, tmp_path: Path) -> None:
        output_path = tmp_path / "report.json"
        _run_script(EVAL_SCRIPT, "--output", str(output_path))
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["pass_rate"] == 1.0, (
            f"Expected pass_rate=1.0 for a clean dataset, got {report['pass_rate']}"
        )
