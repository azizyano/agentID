"""Offline SDK callback demo. Synthetic chain/worker only; zero model calls/writes."""
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/evaluation'))
from veriabstain_eval.application_callback import AnalysisCallback
from veriabstain_eval.dataset import load_manifest
from veriabstain_eval.sdk_fixture import make_sdk_fixture
from veriabstain_eval.runner import offline


async def main():
    manifest,_=load_manifest()
    case=next(c for c in manifest['cases'] if c['condition']=='false_warning')
    ops,client=make_sdk_fixture(case)
    job=client.get_job.return_value
    expected={'jobId':job.id,'client':job.client,'provider':job.provider,'evaluator':job.evaluator,
              'hook':job.hook,'description':job.description,'budget':job.budget,'expiredAt':job.expired_at}
    scope={k:case['claim'][k] for k in ('predicate','chain_id','target','arguments')}
    auth={**scope,'allowed_actions':['analyze'],'deadline':case['now']+100,'max_asset_spend':0}
    evidence={**scope,'schema_version':1,'block_number':123,'block_hash':'0x'+'ab'*32,
              'value':case['read']['value'],'source':'offline-demo','assurance':'SIMULATED_READ',
              'observed_at':case['now'],'finalized':True,'canonical':True,'abi_supported':True,
              'error':None,'conflicting':False}
    worker_calls=[]
    def worker(_auth,ev):
        worker_calls.append(1)
        return json.dumps({k:ev[k] for k in ('predicate','chain_id','target','arguments',
                          'schema_version','block_number','block_hash','value')})
    with tempfile.TemporaryDirectory(prefix='veriabstain-demo-') as directory:
        callback=AnalysisCallback(ops,None,auth,expected,worker,Path(directory)/'journal.db',
                                  collector=lambda *_args,**_kwargs:evidence,clock=lambda:case['now'])
        with offline(),patch('bnbagent.erc8183.job_ops.time.time',return_value=case['now']):
            first=await callback.on_funded({'jobId':job.id})
            replay=await callback.on_funded({'jobId':job.id})
        assert first['accepted_analysis'] and replay['cached'] and len(worker_calls)==1
        client.submit.assert_not_called()
        print(json.dumps({'mode':'OFFLINE_SDK_COMPOSITION_DEMO','receipt':first,
                          'redelivery_cached':True,'scripted_worker_calls':len(worker_calls),
                          'model_calls':0,'transactions':0},indent=2))


if __name__=='__main__':
    asyncio.run(main())
