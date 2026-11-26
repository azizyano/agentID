"""Collect a reviewed read-only testnet predicate; never accepts worker evidence."""
import argparse
import json
import sys
import time
from pathlib import Path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/evaluation'))
from veriabstain_eval.chain_evidence import collect_evidence
from veriabstain_eval.deliverables import Authorization
from veriabstain_eval.workers import strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization', type=Path, required=True)
    parser.add_argument('--save', type=Path, required=True, help='New evidence file; existing files never replaced')
    args = parser.parse_args()
    try:
        with args.authorization.open('rb') as source:
            raw = source.read(65_537)
        if len(raw) > 65_536 or args.save.exists():
            raise ValueError('Oversized input or existing output')
        auth = Authorization.model_validate(strict_json(raw.decode()))
        now = int(time.time())
        if now >= auth.deadline or 'analyze' not in auth.allowed_actions:
            raise ValueError('No current analysis authorization')
        scope = {k: getattr(auth,k) for k in ('predicate','chain_id','target','arguments')}
        w3 = Web3(Web3.HTTPProvider('https://bsc-testnet-dataseed.bnbchain.org', request_kwargs={'timeout':15}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        evidence = collect_evidence(w3, scope, now=now)
        finished = int(time.time())
        if finished >= auth.deadline or not 0 <= finished - evidence['observed_at'] <= 120:
            raise ValueError('Read expired during collection')
        args.save.parent.mkdir(parents=True, exist_ok=True)
        with args.save.open('x', encoding='utf-8') as target:
            json.dump(evidence,target,indent=2)
            target.write('\n')
        print(json.dumps({'status':'EVIDENCE_COLLECTED','assurance':evidence['assurance'],
                          'block_number':evidence['block_number'],'transactions':0}))
        return 0
    except Exception:
        print(json.dumps({'status':'ESCALATE','reason':'EVIDENCE_COLLECTION_FAILED',
                          'transactions':0}),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
