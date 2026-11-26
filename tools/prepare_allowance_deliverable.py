"""Prepare job1766's approved read-only deliverable; never signs or submits."""
import json
import time
from pathlib import Path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from bnbagent.core.abis import load_abi
from reconcile_testnet_job import reconcile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'artifacts/testnet/quote-attempt2'
CREATE = '0x1b66e78e29889946763ba88b5cbdaf35599369b5dbe9af40999a6334c99d10c8'


def prepare(w3, spec):
    evidence = reconcile(w3, spec, CREATE, int(time.time()))
    if (evidence['job_id'] != 1766 or evidence['job_status'] != 'FUNDED'
            or evidence['budget_raw'] != 10**18):
        raise ValueError('Expected exact funded job1766; reconcile before proceeding')
    number = evidence['block_number']
    token = w3.eth.contract(address=spec['payment_token'], abi=load_abi('ERC20.json'))
    allowance = token.functions.allowance(spec['client'], spec['commerce']).call(block_identifier=number)
    if type(allowance) is not int or allowance < 0:
        raise ValueError('Invalid allowance result')
    result = {'chain_id': 97, 'block_number': number, 'block_hash': evidence['block_hash'],
              'token': spec['payment_token'], 'owner': spec['client'],
              'spender': spec['commerce'], 'allowance_raw': allowance}
    # The exact UTF-8 file bytes, including final newline, are the commitment input.
    payload = (json.dumps(result, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    block = w3.eth.get_block(number)
    if Web3.to_hex(block['hash']) != evidence['block_hash']:
        raise ValueError('Pinned block changed')
    policy = w3.eth.contract(address=spec['policy'], abi=load_abi('OptimisticPolicy.json'))
    window = policy.functions.disputeWindow().call(block_identifier=number)
    if block['timestamp'] + window + 60 >= spec['expired_at']:
        raise ValueError('Insufficient submission time; preserve funded job for reconciliation')
    evidence.update({'deliverable_keccak256': Web3.to_hex(Web3.keccak(payload)),
                     'deliverable_file': 'allowance-result.json',
                     'commitment_encoding': 'Keccak256 of exact UTF-8 file bytes including final newline',
                     'dispute_window_seconds': window,
                     'latest_submission_timestamp': spec['expired_at'] - window,
                     'limitations': 'RPC_FINALIZED_READ; no cryptographic eth_call proof or model behavioral evidence',
                     'submission_sent': False})
    return payload, evidence


if __name__ == '__main__':
    if (DIRECTORY / 'allowance-result.json').exists():
        raise ValueError('Deliverable already exists; preserve commitment and reconcile before replacement')
    spec = json.loads((DIRECTORY / 'signed-job.json').read_text())
    w3 = Web3(Web3.HTTPProvider('https://bsc-testnet-dataseed.bnbchain.org', request_kwargs={'timeout': 15}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    payload, evidence = prepare(w3, spec)
    with (DIRECTORY / 'allowance-result.json').open('xb') as output:
        output.write(payload)
    with (DIRECTORY / 'allowance-evidence.json').open('x', encoding='utf-8') as output:
        json.dump(evidence, output, indent=2)
        output.write('\n')
    print(json.dumps({'result': json.loads(payload), 'evidence': evidence}, indent=2))
