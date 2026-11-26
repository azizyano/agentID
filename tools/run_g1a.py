"""Run all frozen fixtures locally. Exit nonzero on an unexpected outcome."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages/evaluation"))
from veriabstain_eval.runner import run_suite

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=root / "artifacts/g1a")
args = parser.parse_args()
summary, results = asyncio.run(run_suite())
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "results.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in results), encoding="utf-8")
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
sys.exit(1 if summary["failed"] or summary["unauthorized_effects"] or summary["duplicate_effects"] else 0)
