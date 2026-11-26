import json

import pytest

from veriabstain_eval.check_analysis import save_receipt
from veriabstain_eval.receipt_inspection import inspect_receipt,list_receipts
from veriabstain_eval.workers import digest


def rejected():
    return {'accepted_analysis':False,'reason':'OUTPUT_VALUE_MISMATCH',
            'recommendation':'ESCALATE','execution_authorized':False,'transactions':0,'model_calls':0}


def test_consistent_receipt_never_implies_truth(tmp_path):
    path=save_receipt(rejected(),tmp_path)
    result=inspect_receipt(path)
    assert result['status']=='CONTENT_CONSISTENT'
    assert result['authenticated'] is False and result['truth_verified'] is False
    assert result['historical_only'] and not result['execution_authorized']
    assert list_receipts(tmp_path)[0]['receipt_id']==path.parent.name


def test_digest_detects_content_edit(tmp_path):
    path=save_receipt(rejected(),tmp_path)
    value=json.loads(path.read_text());value['receipt']['reason']='CHECK_FAILED'
    path.write_text(json.dumps(value))
    assert inspect_receipt(path)['status']=='DIGEST_MISMATCH'


@pytest.mark.parametrize('change',[
    {'execution_authorized':True},{'execution_authorized':0},{'accepted_analysis':True},
    {'transactions':1},{'model_calls':True},{'reason':'secret text'},
    {'assurance':'CRYPTOGRAPHIC_PROOF'},{'raw_output':'private text'},
    {'checked_at':True}])
def test_recomputed_digest_does_not_bypass_schema(tmp_path,change):
    path=save_receipt(rejected(),tmp_path)
    value=json.loads(path.read_text());value['receipt'].update(change)
    value['receipt_digest']=digest(value['receipt']);path.write_text(json.dumps(value))
    result=inspect_receipt(path)
    assert result['status']=='INVALID_RECEIPT'
    assert 'private' not in json.dumps(result) and 'secret' not in json.dumps(result)


def test_duplicate_keys_truncation_and_missing_files(tmp_path):
    path=save_receipt(rejected(),tmp_path)
    original=path.read_text();path.write_text(original[:-2]+',"receipt":{}}')
    assert inspect_receipt(path)['status']=='INVALID_RECEIPT'
    path.write_text('{')
    assert inspect_receipt(path)['status']=='INVALID_RECEIPT'
    assert inspect_receipt(tmp_path/'missing.json')['status']=='INVALID_RECEIPT'


def test_bounded_listing_and_incomplete_receipt(tmp_path):
    for _ in range(3):save_receipt(rejected(),tmp_path)
    assert len(list_receipts(tmp_path,2))==2
    empty=tmp_path/('0'*32);empty.mkdir()
    assert list_receipts(tmp_path,1)[0]['status']=='INVALID_RECEIPT'
    with pytest.raises(ValueError):list_receipts(tmp_path,0)


def test_accepted_receipt_needs_all_bindings(tmp_path):
    receipt={'schema_version':1,'accepted_analysis':True,'reason':'MATCHED_PINNED_EVIDENCE',
             'recommendation':'ACCEPT_ANALYSIS','execution_authorized':False,
             'assurance':'RPC_FINALIZED_READ',**{k:'a'*64 for k in
             ('authorization_digest','evidence_digest','deliverable_digest')}}
    path=save_receipt(receipt,tmp_path)
    assert inspect_receipt(path)['status']=='CONTENT_CONSISTENT'
    del receipt['authorization_digest']
    assert inspect_receipt(save_receipt(receipt,tmp_path))['status']=='INVALID_RECEIPT'
