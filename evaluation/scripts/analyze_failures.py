"""Analyze deterministic PQS summary against NFR-1 threshold targets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def evaluate_threshold(metric: str, observed: float, target: float) -> dict[str, Any]:
	passed = observed <= target
	return {
		"metric": metric,
		"observed_ms": round(observed, 2),
		"target_ms": round(target, 2),
		"status": "PASS" if passed else "FAIL",
		"delta_ms": round(observed - target, 2),
	}


def main() -> int:
	parser = argparse.ArgumentParser(description="Analyze PQS summary for NFR-1 thresholds")
	parser.add_argument(
		"--input",
		type=Path,
		default=Path("evaluation/results/pqs_summary.json"),
		help="Path to PQS summary JSON",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=Path("evaluation/results/pqs_analysis.json"),
		help="Path to write analysis JSON",
	)
	args = parser.parse_args()

	repo_root = Path(__file__).resolve().parents[2]
	input_path = (repo_root / args.input).resolve()
	output_path = (repo_root / args.output).resolve()
	output_path.parent.mkdir(parents=True, exist_ok=True)

	if not input_path.exists():
		print("PQS summary file not found:", input_path)
		return 1

	summary = json.loads(input_path.read_text(encoding="utf-8"))
	aggregate = summary.get("aggregate", {})

	checks = [
		evaluate_threshold("e2e_p95_ms", float(aggregate.get("e2e_p95_ms", 0.0)), 2000.0),
		evaluate_threshold(
			"retrieval_p95_ms", float(aggregate.get("retrieval_p95_ms", 0.0)), 500.0
		),
		evaluate_threshold("ttft_p95_ms", float(aggregate.get("ttft_p95_ms", 0.0)), 500.0),
	]

	overall_status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
	analysis = {
		"generated_at": datetime.now(timezone.utc).isoformat(),
		"source_summary": str(input_path),
		"overall_status": overall_status,
		"checks": checks,
		"notes": [
			"Deterministic scaffold analysis for Step 62 baseline checkpoint.",
			"Use production benchmark runs before promoting NFR-1 to done.",
		],
	}

	output_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")

	print("PQS analysis written:", output_path)
	print("Overall status:", overall_status)
	for item in checks:
		print(
			"- {metric}: {status} (observed={observed}ms, target={target}ms, delta={delta}ms)".format(
				metric=item["metric"],
				status=item["status"],
				observed=item["observed_ms"],
				target=item["target_ms"],
				delta=item["delta_ms"],
			)
		)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
