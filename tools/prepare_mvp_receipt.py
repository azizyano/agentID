"""Prepare one deterministic unsigned Agent ID MVP receipt plan."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/evaluation'))

from veriabstain_eval.mvp_receipt import prepare_receipt_plan
from veriabstain_eval.workers import strict_json

MAX_INPUT_BYTES = 262_144


def load_input(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('Evidence input exceeds supported size')
    try:
        return strict_json(raw.decode('utf-8'))
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ValueError('Evidence input is not supported JSON') from error


def write_plan(plan, directory):
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / 'receipt-plan.json'
    with output.open('x', encoding='utf-8') as target:
        json.dump(plan.model_dump(mode='json'), target, indent=2, allow_nan=False)
        target.write('\n')
        target.flush()
        os.fsync(target.fileno())
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--now', required=True, type=int)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        plan = prepare_receipt_plan(load_input(args.evidence), now=args.now)
        output = write_plan(plan, args.output)
    except (OSError, ValueError, TypeError):
        print(json.dumps({'status': 'MVP_RECEIPT_PREPARATION_FAILED'}), file=sys.stderr)
        return 2
    print(json.dumps({
        'status': 'MVP_RECEIPT_PREPARED',
        'evidenceDigest': plan.evidence_digest,
        'assessmentDigest': plan.assessment_digest,
        'output': str(output),
        'transactionsSent': 0,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
