"""Export an already-simulated signed create plan; no wallet or chain execution."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/evaluation"))
from veriabstain_eval.wallet_funding import funding_script

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan=json.loads(args.plan.read_text())
    if plan.get('valid_until',0)-int(time.time()) < 300:
        raise ValueError('A fresh quote with at least five minutes remaining is required before exporting a new session')
    script = funding_script(plan, json.loads(args.spec.read_text()),
                            json.loads((ROOT/'config/job-proposal.json').read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(script, encoding="utf-8")
    print("Manual-confirmation funding session exported; no transaction sent.")
