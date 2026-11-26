"""Prepare one eligible participant's unsigned BSC mainnet MVP interaction."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/evaluation'))

from veriabstain_eval.mainnet_interaction import prepare_interaction
from veriabstain_eval.workers import strict_json

DEFAULT_RPC = 'https://bsc-dataseed.bnbchain.org'
MAX_PLAN_BYTES = 1_048_576
REGISTRY_ABI = [{
    'inputs': [{'internalType': 'address', 'name': 'owner', 'type': 'address'}],
    'name': 'balanceOf',
    'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
    'stateMutability': 'view',
    'type': 'function',
}]


def load_json(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_PLAN_BYTES:
        raise ValueError('Receipt plan exceeds supported size')
    try:
        return strict_json(raw.decode('utf-8'))
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ValueError('Receipt plan is not supported JSON') from error


def save_exclusive(value, output):
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError('Interaction output already exists')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=destination.parent, delete=False) as target:
            temporary = Path(target.name)
            json.dump(value, target, indent=2, allow_nan=False)
            target.write('\n')
            target.flush()
            os.fsync(target.fileno())
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--participant', required=True)
    parser.add_argument('--receipt-plan', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--rpc-url', default=DEFAULT_RPC, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        build = load_json(ROOT / 'artifacts/mvp/contract-build.json')
        contract_abi = build['contracts']['VeriAbstainEvidenceRegistry']['abi']
        w3 = Web3(Web3.HTTPProvider(args.rpc_url, request_kwargs={'timeout': 20}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        result = prepare_interaction(
            w3,
            args.participant,
            load_json(args.receipt_plan),
            contract_abi,
            REGISTRY_ABI,
        )
        save_exclusive(result, args.output)
    except Exception:
        print(json.dumps({'status': 'MVP_INTERACTION_PREPARATION_FAILED', 'transactionsSent': 0}), file=sys.stderr)
        return 2
    print(json.dumps({
        'status': result['status'],
        'participant': result['participant'],
        'contractAddress': result['contract_address'],
        'expectedFirstInteraction': result['expected_first_interaction'],
        'output': args.output,
        'transactionsSent': 0,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
