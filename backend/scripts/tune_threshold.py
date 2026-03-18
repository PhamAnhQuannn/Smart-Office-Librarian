"""Threshold tuning utility.

Reads a golden questions validation report produced by
``evaluation/scripts/evaluate_golden_questions.py`` and recommends a new
threshold based on the observed pass rate.  With ``--output``, writes the
recommendation to a JSON file for operator review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_MIN_ACCEPTABLE_PASS_RATE = 0.80
_HIGH_PASS_RATE = 0.95
_LOOSEN_STEP = 0.05
_TIGHTEN_STEP = 0.05
_DEFAULT_THRESHOLD = 0.70


def recommend_threshold(current: float, pass_rate: float) -> dict[str, Any]:
    """Return a recommendation dict based on current threshold and observed pass rate."""
    if pass_rate < _MIN_ACCEPTABLE_PASS_RATE:
        action = "loosen"
        recommended = round(min(1.0, current + _LOOSEN_STEP), 4)
        reason = (
            f"Pass rate {pass_rate:.1%} is below minimum {_MIN_ACCEPTABLE_PASS_RATE:.0%}. "
            "Raising threshold reduces strictness and should recover failing questions."
        )
    elif pass_rate >= _HIGH_PASS_RATE:
        action = "tighten"
        recommended = round(max(0.0, current - _TIGHTEN_STEP), 4)
        reason = (
            f"Pass rate {pass_rate:.1%} is at or above {_HIGH_PASS_RATE:.0%}. "
            "Lowering threshold increases strictness while the system can handle it."
        )
    else:
        action = "keep"
        recommended = current
        reason = (
            f"Pass rate {pass_rate:.1%} is within the acceptable band "
            f"[{_MIN_ACCEPTABLE_PASS_RATE:.0%}, {_HIGH_PASS_RATE:.0%}). No change needed."
        )

    return {
        "current_threshold": current,
        "recommended_threshold": recommended,
        "action": action,
        "reason": reason,
        "pass_rate": round(pass_rate, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend or apply threshold tuning")
    parser.add_argument(
        "--eval-file",
        type=Path,
        required=True,
        help="Path to golden questions validation report JSON",
    )
    parser.add_argument(
        "--current-threshold",
        type=float,
        default=_DEFAULT_THRESHOLD,
        help=f"Current threshold value (default: {_DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write recommendation JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print recommendation without writing output file",
    )
    args = parser.parse_args()

    if not args.eval_file.exists():
        print(f"Evaluation file not found: {args.eval_file}")
        return 1

    try:
        report = json.loads(args.eval_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Failed to parse evaluation file: {exc}")
        return 1

    pass_rate = float(report.get("pass_rate", 0.0))
    recommendation = recommend_threshold(args.current_threshold, pass_rate)

    print(f"Current threshold : {recommendation['current_threshold']}")
    print(f"Pass rate         : {recommendation['pass_rate']:.1%}")
    print(f"Action            : {recommendation['action']}")
    print(f"Recommended       : {recommendation['recommended_threshold']}")
    print(f"Reason            : {recommendation['reason']}")

    if not args.dry_run and args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(recommendation, indent=2), encoding="utf-8")
        print(f"Recommendation written: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
