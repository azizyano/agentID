"""Check a saved Agentic Wallet preview or account-selection observation locally."""

import argparse
import json
import sys
import time
from pathlib import Path

from veriabstain_eval.wallet_compatibility import (
    CompatibilityCase,
    MAX_REPORT_BYTES,
    PreviewReportCase,
    check_compatibility,
    compare_compatibility,
    parse_compatibility_case,
    render_comparison_markdown,
    render_compatibility_markdown,
)


def read_case(path: Path) -> CompatibilityCase | PreviewReportCase:
    with path.open("rb") as source:
        return parse_compatibility_case(source.read(MAX_REPORT_BYTES + 1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True, help="Expected call and one redacted observation.")
    parser.add_argument("--now", type=int, help="Unix seconds at which to evaluate the observation.")
    parser.add_argument("--baseline", type=Path, help="Earlier observation for the same expected action.")
    parser.add_argument("--baseline-now", type=int, help="Baseline evaluation time in Unix seconds. Defaults to --now.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json", help="Output format.")
    args = parser.parse_args()
    if args.baseline_now is not None and args.baseline is None:
        parser.error("--baseline-now requires --baseline")
    now = int(time.time()) if args.now is None else args.now

    try:
        case = read_case(args.case)
        if args.baseline is None:
            report = check_compatibility(case, now)
        else:
            baseline_now = now if args.baseline_now is None else args.baseline_now
            report = compare_compatibility(read_case(args.baseline), case, baseline_now=baseline_now, current_now=now)
    except (OSError, ValueError):
        status = "INVALID_CASE" if args.baseline is None else "INVALID_COMPARISON"
        print(json.dumps({"status": status}), file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2))
    elif args.baseline is None:
        print(render_compatibility_markdown(case, report))
    else:
        print(render_comparison_markdown(report))
    final_assessment = report if args.baseline is None else report["after"]
    return 0 if final_assessment["status"] == "PREVIEW_MATCHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
