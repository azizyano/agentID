"""Validate local JSON against trusted authorization/evidence; no external calls."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/evaluation'))
from veriabstain_eval.deliverables import validate_deliverable
from veriabstain_eval.workers import strict_json


def read(path):
    with path.open('rb') as source:
        data = source.read(65_537)
    if len(data) > 65_536:
        raise ValueError('Input exceeds limit')
    return data.decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Untrusted deliverable JSON file')
    parser.add_argument('--authorization', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--now', type=int, required=True, help='Explicit trusted evaluation timestamp')
    args = parser.parse_args()
    try:
        result = validate_deliverable(read(args.output), strict_json(read(args.authorization)),
                                      strict_json(read(args.evidence)), now=args.now)
    except (OSError, ValueError, UnicodeError):
        result = {'accepted_analysis': False, 'reason': 'INVALID_INPUT_FILE',
                  'recommendation': 'ESCALATE', 'execution_authorized': False}
    print(json.dumps(result, indent=2))
    return 0 if result['accepted_analysis'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
