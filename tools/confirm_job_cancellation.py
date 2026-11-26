"""Verify the exact user cancellation and closed zero-budget job, read-only."""
import argparse
import json
import time
from pathlib import Path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from bnbagent.core.abis import load_abi
from reconcile_testnet_job import reconcile, CREATE_TX

ROOT=Path(__file__).resolve().parents[1]


def confirm(w3, spec, transaction_hash):
    report=reconcile(w3,spec,CREATE_TX,int(time.time()))
    if report['job_id']!=1765 or report['job_status']!='REJECTED' or report['budget_raw']!=0 or report['commerce_allowance_raw']!=0:
        raise ValueError('Original job is not closed with zero escrow/allowance')
    receipt=w3.eth.get_transaction_receipt(transaction_hash)
    tx=w3.eth.get_transaction(transaction_hash)
    commerce=w3.eth.contract(address=spec['commerce'],abi=load_abi('AgenticCommerce.json'))
    expected=commerce.encode_abi('reject',args=[1765,Web3.keccak(text='VERIABSTAIN_EXPIRED_UNFUNDED_QUOTE'),b''])
    if (type(receipt['status']) is not int or receipt['status']!=1 or receipt['blockNumber']>report['block_number']
            or receipt['blockHash']!=w3.eth.get_block(receipt['blockNumber'])['hash']
            or Web3.to_hex(receipt['transactionHash']).lower()!=transaction_hash.lower()
            or tx['from'].lower()!=spec['client'].lower() or tx['to'].lower()!=spec['commerce'].lower()
            or tx['value']!=0 or Web3.to_hex(tx['input']).lower()!=expected.lower()):
        raise ValueError('Cancellation receipt does not match the exact reviewed transaction')
    return {**report,'status':'CANCELLED_UNFUNDED_CONFIRMED','cancellation_transaction_hash':transaction_hash,
            'cancellation_block_number':receipt['blockNumber'],'cancellation_block_hash':Web3.to_hex(receipt['blockHash']),
            'original_quote_hash':spec['quote']['negotiation_hash'],'transactions_sent':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hash',required=True)
    args=parser.parse_args()
    if len(args.hash)!=66 or not args.hash.startswith('0x'):
        raise ValueError('Expected public transaction hash')
    bytes.fromhex(args.hash[2:])
    spec=json.loads((ROOT/'artifacts/testnet/quote/signed-job.json').read_text())
    w3=Web3(Web3.HTTPProvider('https://bsc-testnet-dataseed.bnbchain.org',request_kwargs={'timeout':15}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware,layer=0)
    report=confirm(w3,spec,args.hash)
    output=ROOT/'artifacts/testnet/cancellation-confirmed.json'
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
