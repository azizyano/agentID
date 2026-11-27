"""Check a saved Agentic Wallet preview or account-selection observation locally."""

import argparse
import json
import sys
import time
from pathlib import Path

from veriabstain_eval.wallet_compatibility import (
    CompatibilityCase,
    MAX_REPORT_BYTES,
    check_compatibility,
)
from veriabstain_eval.workers import strict_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True, help="Expected call and one redacted observation.")
    parser.add_argument("--now", type=int, help="Unix seconds at which to evaluate the observation.")
    args = parser.parse_args()
    now = int(time.time()) if args.now is None else args.now

    try:
        with args.case.open("rb") as source:
            raw = source.read(MAX_REPORT_BYTES + 1)
        if len(raw) > MAX_REPORT_BYTES:
            raise ValueError("Case exceeds the size limit")
        case = CompatibilityCase.model_validate(strict_json(raw.decode("utf-8")))
        report = check_compatibility(case, now)
    except (OSError, ValueError):
        print(json.dumps({"status": "INVALID_CASE"}), file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PREVIEW_MATCHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
