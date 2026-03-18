"""Validate golden questions dataset for the N-35 evaluation gate.

Checks the structural integrity of each entry in
``evaluation/datasets/golden_questions_v1.json`` and produces a validation
summary report.  This script is intentionally self-contained so it runs in CI
without live external services.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"id", "question", "expected_answer_keywords", "namespace", "min_confidence"}
)
VALID_CONFIDENCE_LEVELS: frozenset[str] = frozenset({"HIGH", "MEDIUM", "LOW"})


def validate_entry(entry: Any) -> list[str]:
    """Return a list of validation error messages for a single dataset entry."""
    errors: list[str] = []
    if not isinstance(entry, dict):
        return ["Entry is not a JSON object"]
    for field in REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"Missing required field: {field!r}")
    if "question" in entry and not str(entry.get("question", "")).strip():
        errors.append("Field 'question' must be non-empty")
    if "expected_answer_keywords" in entry:
        kws = entry["expected_answer_keywords"]
        if not isinstance(kws, list) or len(kws) == 0:
            errors.append("Field 'expected_answer_keywords' must be a non-empty list")
    if "min_confidence" in entry and entry["min_confidence"] not in VALID_CONFIDENCE_LEVELS:
        errors.append(
            f"Field 'min_confidence' must be one of {sorted(VALID_CONFIDENCE_LEVELS)}, "
            f"got: {entry['min_confidence']!r}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate golden questions dataset")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evaluation/datasets/golden_questions_v1.json"),
        help="Path to golden questions JSON file (relative to repo root)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/results/golden_questions_validation.json"),
        help="Path to write validation report",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    dataset_path = (repo_root / args.dataset).resolve()
    output_path = (repo_root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not dataset_path.exists():
        print(f"Dataset file not found: {dataset_path}")
        return 1

    try:
        raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Failed to parse dataset JSON: {exc}")
        return 1

    if not isinstance(raw, list):
        print("Dataset must be a JSON array")
        return 1

    entry_results: list[dict[str, Any]] = []
    for idx, entry in enumerate(raw):
        errors = validate_entry(entry)
        entry_id = entry.get("id", f"entry_{idx}") if isinstance(entry, dict) else f"entry_{idx}"
        entry_results.append(
            {
                "id": entry_id,
                "status": "PASS" if not errors else "FAIL",
                "errors": errors,
            }
        )

    total = len(entry_results)
    passed = sum(1 for r in entry_results if r["status"] == "PASS")
    failed = total - passed
    overall_status = "PASS" if failed == 0 and total > 0 else "FAIL"

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "evaluation/scripts/evaluate_golden_questions.py",
        "dataset": str(dataset_path),
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4) if total > 0 else 0.0,
        "overall_status": overall_status,
        "results": entry_results,
    }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Validation report written: {output_path}")
    print(f"Overall status: {overall_status} ({passed}/{total} questions passed)")
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
