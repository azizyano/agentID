import json
from pathlib import Path

from veriabstain_eval.check_analysis import check_analysis,save_receipt
from veriabstain_eval.workers import digest

ROOT=Path(__file__).resolve().parents[2]


def context():
    p=ROOT/'examples/deliverable-validation'
    return (json.loads((p/'authorization.json').read_text()),
            (p/'output.json').read_text(),json.loads((p/'evidence.json').read_text()))


def test_independent_collector_receives_candidate_block_and_approved_scope():
    auth,output,evidence=context();calls=[]
    def collector(w3,scope,**kwargs):
        calls.append((scope,kwargs));return evidence
    result=check_analysis(None,auth,output,collector=collector,clock=lambda:1000)
    assert result['accepted_analysis'] and not result['execution_authorized']
    assert calls[0][1]=={'now':1000,'pinned_block_number':10}
    assert 'value' not in calls[0][0]


def test_wrong_scope_never_queries_rpc():
    auth,output,evidence=context();parsed=json.loads(output);parsed['chain_id']=56
    def forbidden(*_args,**_kwargs):raise AssertionError('RPC called')
    result=check_analysis(None,auth,json.dumps(parsed),collector=forbidden,clock=lambda:1000)
    assert result['reason']=='OUTPUT_SCOPE_MISMATCH'


def test_provider_failure_and_wrong_value_fail_closed():
    auth,output,evidence=context()
    def failure(*_args,**_kwargs):raise OSError('secret endpoint')
    result=check_analysis(None,auth,output,collector=failure,clock=lambda:1000)
    assert result['reason']=='CHECK_FAILED' and 'secret' not in json.dumps(result)
    evidence['value']=100
    result=check_analysis(None,auth,output,collector=lambda *_args,**_kwargs:evidence,clock=lambda:1000)
    assert result['reason']=='OUTPUT_VALUE_MISMATCH'


def test_deadline_expiring_during_read_is_rejected():
    auth,output,evidence=context();times=iter([1000,1200,1200])
    result=check_analysis(None,auth,output,collector=lambda *_args,**_kwargs:evidence,clock=lambda:next(times))
    assert result['reason']=='AUTHORIZATION_BLOCKED'


def test_receipts_are_distinct_and_content_bound(tmp_path):
    receipt={'accepted_analysis':False,'reason':'TEST','execution_authorized':False}
    one=save_receipt(receipt,tmp_path);two=save_receipt(receipt,tmp_path)
    assert one!=two and one.read_bytes()==two.read_bytes()
    stored=json.loads(one.read_text())
    assert stored['receipt_digest']==digest(receipt)
    assert len(list(tmp_path.rglob('receipt.json')))==2
