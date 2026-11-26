"""Confirm an exact finalized MVP deployment using public BSC mainnet RPC."""
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

from veriabstain_eval.mainnet_deployment import confirm_deployment
from veriabstain_eval.mainnet_preflight import load_deployment_package

DEFAULT_RPC = 'https://bsc-dataseed.bnbchain.org'


def save(report, output):
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError('Confirmation output already exists')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=destination.parent, delete=False) as target:
            temporary = Path(target.name)
            json.dump(report, target, indent=2, allow_nan=False)
            target.write('\n')
            target.flush()
            os.fsync(target.fileno())
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transaction-hash', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--rpc-url', default=DEFAULT_RPC, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        plan, _ = load_deployment_package(ROOT / 'artifacts/mvp/deployment-package')
        build = json.loads((ROOT / 'artifacts/mvp/contract-build.json').read_text(encoding='utf-8'))
        abi = build['contracts']['VeriAbstainEvidenceRegistry']['abi']
        w3 = Web3(Web3.HTTPProvider(args.rpc_url, request_kwargs={'timeout': 20}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        report = confirm_deployment(w3, args.transaction_hash, plan, abi)
        save(report, args.output)
    except Exception:
        print(json.dumps({'status': 'MVP_DEPLOYMENT_CONFIRMATION_FAILED', 'transactionsSent': 0}), file=sys.stderr)
        return 2
    print(json.dumps({
        'status': report['status'],
        'contractAddress': report['contract_address'],
        'transactionHash': report['transaction_hash'],
        'runtimeCodeKeccak256': report['runtime_code_keccak256'],
        'output': args.output,
        'transactionsSent': 0,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
