from types import SimpleNamespace

import pytest
from web3 import Web3

from veriabstain_eval import chain_evidence as module
from veriabstain_eval.deliverables import validate_deliverable
import json


class FakeEth:
    chain_id = 97
    block = {'number':10,'timestamp':990,'hash':bytes.fromhex('ab'*32)}
    code = b'reviewed-fixture-code'
    changed_hash = False
    status = 3
    job_exists = True

    def __init__(self):
        self.read_blocks = []

    def get_block(self, selector):
        block = dict(self.block)
        if selector != 'finalized' and self.changed_hash:
            block['hash'] = bytes.fromhex('cd'*32)
        return block

    def get_code(self, address, block_identifier):
        self.read_blocks.append(block_identifier)
        return self.code

    def get_storage_at(self, target, slot, block_identifier):
        self.read_blocks.append(block_identifier)
        return bytes(12)+bytes.fromhex(module.PINNED.commerce_impl[2:])

    def contract(self, **kwargs):
        def call(value):
            def read(*,block_identifier):
                self.read_blocks.append(block_identifier)
                return value
            return SimpleNamespace(call=read)
        return SimpleNamespace(functions=SimpleNamespace(
            allowance=lambda *_:call(0),
            getJob=lambda jid:call((jid if self.job_exists else 0,None,None,None,None,10**18,1200,self.status,None,990,bytes(32)))))


@pytest.fixture
def rpc(monkeypatch):
    eth = FakeEth()
    hashed = Web3.to_hex(Web3.keccak(eth.code))
    for field in ('TOKEN_HASH','PROXY_HASH','REVIEWED_COMMERCE_CODE_HASH'):
        monkeypatch.setattr(module,field,hashed)
    return SimpleNamespace(eth=eth)


def scope(job=False):
    return {'predicate':'erc8183.job_status' if job else 'erc20.allowance',
            'chain_id':97,'target':module.COMMERCE if job else module.TOKEN,
            'arguments':{'job_id':1766} if job else {'owner':'0x'+'34'*20,'spender':module.COMMERCE}}


@pytest.mark.parametrize('job',[False,True])
def test_pinned_read_integrates_with_validator(rpc,job):
    context=scope(job)
    evidence=module.collect_evidence(rpc,context,now=1000)
    assert evidence['value']==('COMPLETED' if job else 0)
    assert all(number==10 for number in rpc.eth.read_blocks)
    output={k:v for k,v in evidence.items() if k not in {'source','assurance','observed_at','finalized','canonical','abi_supported','error','conflicting'}}
    auth={**context,'deadline':1100,'allowed_actions':['analyze'],'max_asset_spend':0}
    result=validate_deliverable(json.dumps(output),auth,evidence,now=1000)
    assert result['accepted_analysis'] and not result['execution_authorized']
    assert result['assurance']=='RPC_FINALIZED_READ'


@pytest.mark.parametrize('kind',['wrong_chain','stale','future','reorg','code','unknown_target','missing_job','unknown_status'])
def test_failed_checks(rpc,kind):
    context=scope(kind in ('missing_job','unknown_status'))
    if kind=='wrong_chain':rpc.eth.chain_id=56
    if kind=='stale':rpc.eth.block={**rpc.eth.block,'timestamp':800}
    if kind=='future':rpc.eth.block={**rpc.eth.block,'timestamp':1001}
    if kind=='reorg':rpc.eth.changed_hash=True
    if kind=='code':rpc.eth.code=b'changed'
    if kind=='unknown_target':context['target']='0x'+'11'*20
    if kind=='missing_job':rpc.eth.job_exists=False
    if kind=='unknown_status':rpc.eth.status=99
    with pytest.raises(ValueError):module.collect_evidence(rpc,context,now=1000)


def test_rpc_failure_is_not_success(rpc):
    def fail(*_):raise OSError('Provider unavailable')
    rpc.eth.get_block=fail
    with pytest.raises(OSError):module.collect_evidence(rpc,scope(),now=1000)


def test_implementation_drift(rpc):
    rpc.eth.get_storage_at=lambda *_args,**_kwargs:bytes(12)+bytes.fromhex('11'*20)
    with pytest.raises(ValueError,match='implementation changed'):
        module.collect_evidence(rpc,scope(True),now=1000)


@pytest.mark.parametrize('number',[11,-1,True])
def test_candidate_block_must_be_finalized_valid_integer(rpc,number):
    with pytest.raises(ValueError):
        module.collect_evidence(rpc,scope(),now=1000,pinned_block_number=number)


def test_fresh_finalized_candidate_block(rpc):
    result=module.collect_evidence(rpc,scope(),now=1000,pinned_block_number=10)
    assert result['block_number']==10 and result['value']==0
