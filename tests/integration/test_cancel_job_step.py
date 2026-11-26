import importlib.util
import json
from pathlib import Path
import subprocess

import pytest
from web3 import Web3
from bnbagent.core.abis import load_abi

ROOT=Path(__file__).resolve().parents[2]
entry=importlib.util.spec_from_file_location('cancel_export',ROOT/'tools/export_cancel_job_step.py')
module=importlib.util.module_from_spec(entry);entry.loader.exec_module(module)


def fixture():
    spec=json.loads((ROOT/'artifacts/testnet/quote/signed-job.json').read_text())
    report={'job_status':'OPEN','budget_raw':0,'quote_expired':True,'commerce_allowance_raw':0,
            'client':spec['client'],'provider':spec['provider'],'payment_token':spec['payment_token'],'job_id':1765}
    contract=Web3().eth.contract(address=spec['commerce'],abi=load_abi('AgenticCommerce.json'))
    report['unsigned_cancellation_for_review']={'chainId':97,'from':spec['client'],'to':spec['commerce'],'value':0,
      'data':contract.encode_abi('reject',args=[1765,Web3.keccak(text='VERIABSTAIN_EXPIRED_UNFUNDED_QUOTE'),b''])}
    return report,spec


@pytest.mark.parametrize('field,value',[('job_status','FUNDED'),('budget_raw',1),('commerce_allowance_raw',1),('quote_expired',False)])
def test_cancel_requires_reconciled_zero_exposure(field,value):
    report,spec=fixture();report[field]=value
    with pytest.raises(ValueError):module.cancel_script(report,spec)


def test_cancel_rejects_changed_transaction():
    report,spec=fixture();report['unsigned_cancellation_for_review']['data']='0x00'
    with pytest.raises(ValueError):module.cancel_script(report,spec)


def test_cancel_exports_only_explicit_review_request(tmp_path):
    report,spec=fixture();script=module.cancel_script(report,spec)
    assert 'eth_sendTransaction' in script and 'PUBLIC_CANCEL_JOB_TXHASH' in script
    assert 'j.status!==0n' in script and 'j.budget!==0n' in script
    path=tmp_path/'cancel.js';path.write_text(script)
    result=subprocess.run(['node','--check',str(path)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
