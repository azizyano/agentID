"""Check a supplied analysis with independent public testnet reads and save receipt."""
import argparse
import json
import sys
from pathlib import Path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/evaluation'))
from veriabstain_eval.check_analysis import check_analysis, save_receipt
from veriabstain_eval.workers import strict_json


def read(path):
    with path.open('rb') as source:
        raw=source.read(65_537)
    if len(raw)>65_536:
        raise ValueError('Input too large')
    return raw.decode('utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization',type=Path,required=True)
    parser.add_argument('--analysis',type=Path,required=True)
    args=parser.parse_args()
    try:
        authorization=strict_json(read(args.authorization))
        output=read(args.analysis)
        w3=Web3(Web3.HTTPProvider('https://bsc-testnet-dataseed.bnbchain.org',request_kwargs={'timeout':15}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware,layer=0)
        receipt=check_analysis(w3,authorization,output)
        path=save_receipt(receipt,ROOT/'artifacts/private/analysis-receipts')
        print(json.dumps({'status':'ACCEPTED' if receipt['accepted_analysis'] else 'ESCALATE',
                          'reason':receipt['reason'],'receipt_path':str(path),
                          'transactions':0,'model_calls':0}))
        return 0 if receipt['accepted_analysis'] else 2
    except Exception:
        print(json.dumps({'status':'ESCALATE','reason':'INPUT_OR_RECEIPT_FAILURE',
                          'transactions':0,'model_calls':0}),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
