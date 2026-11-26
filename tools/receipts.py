"""List/inspect private analysis receipts locally; no external calls or raw output."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/evaluation'))
from veriabstain_eval.receipt_inspection import inspect_receipt,list_receipts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id',help='Inspect one32character receipt ID')
    parser.add_argument('--limit',type=int,default=100)
    args=parser.parse_args()
    directory=ROOT/'artifacts/private/analysis-receipts'
    try:
        if args.id is not None:
            if not re.fullmatch(r'[0-9a-f]{32}',args.id) or directory.is_symlink() or directory.is_junction():
                raise ValueError('Invalid receipt location')
            report=inspect_receipt(directory/args.id/'receipt.json')
            print(json.dumps(report,indent=2))
            return 0 if report['status']=='CONTENT_CONSISTENT' else 2
        entries=list_receipts(directory,args.limit)
        print(json.dumps({'receipts':entries,'returned':len(entries),'limit':args.limit,
                          'authenticated':False,'truth_verified':False},indent=2))
        return 0 if all(r['status']=='CONTENT_CONSISTENT' for r in entries) else 2
    except (ValueError,OSError):
        print(json.dumps({'status':'RECEIPT_INSPECTION_FAILED','authenticated':False}),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
