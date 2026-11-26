import importlib.util
import json
from pathlib import Path
import subprocess

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import pytest

from bnbagent.core.abis import load_abi
from bnbagent.erc8183.negotiation import build_job_description
from veriabstain_eval.job_quote import prepare_quote, import_signature
from veriabstain_eval.testnet_plan import PINNED
from veriabstain_eval.wallet_funding import funding_script
from veriabstain_eval.testnet_deployment import REVIEWED_COMMERCE_CODE_HASH

ROOT=Path(__file__).resolve().parents[2]


def fixture():
    proposal=json.loads((ROOT/'config/job-proposal.json').read_text())
    draft=json.loads((ROOT/'config/testnet-job.draft.json').read_text())
    account=Account.create(); proposal['provider']=draft['provider']=account.address
    request=prepare_quote(proposal,draft,1795183968)
    signature=Web3.to_hex(account.sign_message(encode_defunct(text=request['message_to_sign'])).signature)
    spec=import_signature(request,signature,proposal,draft,1795183970)
    abi=load_abi('AgenticCommerce.json')
    contract=Web3().eth.contract(address=spec['commerce'],abi=abi)
    data=contract.encode_abi('createJob',args=[spec['provider'],spec['router'],spec['expired_at'],build_job_description(spec['quote']),spec['router']])
    hashes={key:Web3.to_hex(Web3.keccak(b'fixture code')) for key in ['commerce','router','policy','payment_token','router_implementation']}
    hashes['commerce_implementation']=REVIEWED_COMMERCE_CODE_HASH
    plan={'status':'UNSIGNED_PLAN','stage':'CREATE_JOB','chain_id':97,'valid_until':request['expires_at'],
          'code_hashes':hashes,'next_transaction':{'chainId':97,'from':spec['client'],'to':spec['commerce'],'value':0,'data':data}}
    return plan,spec,proposal


def test_real_abi_simulated_wallet_session(tmp_path):
    plan,spec,proposal=fixture()
    script=funding_script(plan,spec,proposal)
    prefix='  const cfg = '
    line=next(line for line in script.splitlines() if line.startswith(prefix))
    cfg=json.loads(line[len(prefix):-1])
    # VM returns synthetic code; use its digest only within the test config.
    cfg['testCode']={k:'0x1234' for k in ['commerce','router','policy','payment_token']}
    for address in cfg['implementations'].values(): cfg['testCode'][address.lower()]='0x1234'
    cfg['codeHashes']={k:Web3.to_hex(Web3.keccak(bytes.fromhex('1234'))) for k in cfg['codeHashes']}
    template=script.replace(line,'  const cfg = __CONFIG__;')
    js=tmp_path/'funding.js'; js.write_text(template)
    config=tmp_path/'config.json'; config.write_text(json.dumps(cfg))
    run=subprocess.run(['node',str(ROOT/'tests/js/wallet_funding_test.cjs'),str(js),str(config)],capture_output=True,text=True,timeout=30)
    assert run.returncode==0,run.stdout+run.stderr
    assert '12 funding-session scenarios passed' in run.stdout


def test_export_rejects_changed_create_calldata():
    plan,spec,proposal=fixture(); plan['next_transaction']['data']='0x00'
    with pytest.raises(ValueError,match='differs'):
        funding_script(plan,spec,proposal)


def test_export_rejects_expanded_budget():
    plan,spec,proposal=fixture(); spec['budget']=2*10**18
    with pytest.raises(ValueError,match='one-U'):
        funding_script(plan,spec,proposal)
