"""Run a read-only BSC mainnet preflight for the exact MVP deployment."""
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

from veriabstain_eval.mainnet_preflight import load_deployment_package, preflight_mainnet

DEFAULT_RPC = 'https://bsc-dataseed.bnbchain.org'


def write_exclusive(report, output):
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError('Preflight output already exists')
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
    parser.add_argument('--deployer', required=True)
    parser.add_argument('--package', default=str(ROOT / 'artifacts/mvp/deployment-package'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--rpc-url', default=DEFAULT_RPC, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        plan, _ = load_deployment_package(args.package)
        w3 = Web3(Web3.HTTPProvider(args.rpc_url, request_kwargs={'timeout': 20}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        report = preflight_mainnet(w3, args.deployer, plan)
        write_exclusive(report, args.output)
    except Exception:
        print(json.dumps({'status': 'MAINNET_PREFLIGHT_FAILED', 'transactionsSent': 0}), file=sys.stderr)
        return 2
    print(json.dumps({
        'status': report['status'],
        'deployer': report['deployer'],
        'balanceSufficient': report['balance_sufficient'],
        'deployerHoldsAgentId': report['deployer_holds_agent_id'],
        'maximumEstimatedCostWei': report['maximum_estimated_cost_wei'],
        'output': args.output,
        'transactionsSent': 0,
    }))
    return 0 if report['status'] == 'MAINNET_PREFLIGHT_READY' else 3


if __name__ == '__main__':
    raise SystemExit(main())
