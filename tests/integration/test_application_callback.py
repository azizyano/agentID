import asyncio
import json
from dataclasses import replace
from unittest.mock import patch

import pytest

from veriabstain_eval.application_callback import AnalysisCallback
from veriabstain_eval.dataset import load_manifest
from veriabstain_eval.sdk_fixture import make_sdk_fixture
from veriabstain_eval.runner import offline


def setup(tmp_path, *, worker=None, collector=None):
    manifest,_=load_manifest()
    case=next(c for c in manifest['cases'] if c['condition']=='false_warning')
    ops,client=make_sdk_fixture(case)
    job=client.get_job.return_value
    expected={'jobId':job.id,'client':job.client,'provider':job.provider,'evaluator':job.evaluator,
              'hook':job.hook,'description':job.description,'budget':job.budget,'expiredAt':job.expired_at}
    scope={k:case['claim'][k] for k in ('predicate','chain_id','target','arguments')}
    auth={**scope,'deadline':case['now']+100,'allowed_actions':['analyze'],'max_asset_spend':0}
    evidence={**scope,'schema_version':1,'block_number':123,'block_hash':'0x'+'ab'*32,
              'value':case['read']['value'],'source':'callback-fixture','assurance':'SIMULATED_READ',
              'observed_at':case['now'],'finalized':True,'canonical':True,'abi_supported':True,
              'error':None,'conflicting':False}
    calls=[]
    def read(*_args,**_kwargs):
        calls.append('read');return evidence
    def answer(_auth,ev):
        calls.append('worker')
        return json.dumps({k:v for k,v in ev.items() if k not in {'source','assurance','observed_at','finalized','canonical','abi_supported','error','conflicting'}})
    callback=AnalysisCallback(ops,None,auth,expected,worker or answer,tmp_path/'callback.db',
                              collector=collector or read,clock=lambda:case['now'])
    return callback,client,case,calls


@pytest.mark.asyncio
async def test_real_sdk_verification_and_redelivery(tmp_path):
    callback,client,case,calls=setup(tmp_path)
    with offline(),patch('bnbagent.erc8183.job_ops.time.time',return_value=case['now']):
        first=await callback.on_funded({'jobId':1})
        second=await callback.on_funded({'jobId':1})
    assert first['accepted_analysis'] and second['cached']
    assert calls==['read','worker']
    assert not first['execution_authorized'] and not first['submission_performed']
    client.submit.assert_not_called()


@pytest.mark.asyncio
async def test_sdk_refusal_blocks_worker(tmp_path):
    callback,client,case,calls=setup(tmp_path)
    client.get_job.return_value=replace(client.get_job.return_value,budget=0)
    with offline(),patch('bnbagent.erc8183.job_ops.time.time',return_value=case['now']):
        result=await callback.on_funded({'jobId':1})
    assert result['reason']=='SDK_VERIFICATION_FAILED' and calls==[]


@pytest.mark.asyncio
async def test_worker_mutation_cannot_rewrite_evidence(tmp_path):
    def worker(auth,ev):
        ev['value']=999
        auth['max_asset_spend']=999
        return json.dumps({k:v for k,v in ev.items() if k not in {'source','assurance','observed_at','finalized','canonical','abi_supported','error','conflicting'}})
    callback,client,case,calls=setup(tmp_path,worker=worker)
    with offline(),patch('bnbagent.erc8183.job_ops.time.time',return_value=case['now']):
        result=await callback.on_funded({'jobId':1})
    assert result['reason']=='OUTPUT_VALUE_MISMATCH'
    assert callback.authorization['max_asset_spend']==0


@pytest.mark.asyncio
async def test_failure_stays_reserved_and_no_retry(tmp_path):
    def worker(*_):raise TimeoutError('private error')
    callback,client,case,calls=setup(tmp_path,worker=worker)
    with offline(),patch('bnbagent.erc8183.job_ops.time.time',return_value=case['now']):
        first=await callback.on_funded({'jobId':1})
        second=await callback.on_funded({'jobId':1})
    assert first['reason']=='RECONCILE_FAILED_ANALYSIS'
    assert second['reason']=='RECONCILE_PENDING_ANALYSIS'
    assert 'private' not in json.dumps(first)


@pytest.mark.asyncio
async def test_concurrent_delivery_single_worker(tmp_path):
    entered=asyncio.Event();release=asyncio.Event();invocations=[]
    async def worker(*_):
        invocations.append(1);entered.set();await release.wait();return '{}'
    callback,client,case,calls=setup(tmp_path,worker=worker)
    with offline(),patch('bnbagent.erc8183.job_ops.time.time',return_value=case['now']):
        task=asyncio.create_task(callback.on_funded({'jobId':1}))
        await entered.wait()
        second=await callback.on_funded({'jobId':1})
        release.set();await task
    assert second['reason']=='RECONCILE_PENDING_ANALYSIS' and len(invocations)==1


@pytest.mark.asyncio
async def test_actual_watcher_calls_async_bound_method(tmp_path):
    from bnbagent.erc8183.job_ops import funded_job_watcher
    callback,client,case,calls=setup(tmp_path)
    stop=asyncio.Event();stop.set()
    with offline(),patch('bnbagent.erc8183.job_ops.time.time',return_value=case['now']):
        await funded_job_watcher(callback.ops,callback.on_funded,stop=stop,interval=.001,max_attempts=1)
    assert calls==['read','worker']
    client.submit.assert_not_called()


@pytest.mark.asyncio
async def test_job_context_change_is_rejected_before_worker(tmp_path):
    callback,client,case,calls=setup(tmp_path)
    callback.expected['budget']+=1
    with offline(),patch('bnbagent.erc8183.job_ops.time.time',return_value=case['now']):
        result=await callback.on_funded({'jobId':1})
    assert result['reason']=='JOB_BINDING_MISMATCH' and not calls
