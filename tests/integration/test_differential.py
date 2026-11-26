"""G3 harness regressions; use frozen outcomes without retuning either checker."""
import ast
import copy
import json
from pathlib import Path

import pytest

from veriabstain_eval.deterministic_baseline import assess_baseline
from veriabstain_eval.differential import _invoke,stats,advantage_gates,same_outcomes
from veriabstain_eval.mutation_manifest import load_corpus,ROOT
from veriabstain_eval.workers import strict_json

CORPUS,_=load_corpus()


@pytest.mark.parametrize('case',CORPUS['cases'],ids=lambda c:c['case_id'])
def test_independent_baseline_matches_frozen_semantics(case):
    package=strict_json(case['input_json']);before=copy.deepcopy(package)
    result=assess_baseline(package,now=case['now'])
    assert {k:result[k] for k in case['expected']}==case['expected']
    assert package==before and result['execution_authorized'] is False


def test_baseline_has_no_candidate_or_oracle_imports():
    source=(ROOT/'packages/evaluation/veriabstain_eval/deterministic_baseline.py').read_text()
    tree=ast.parse(source);imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):imports.extend(n.name for n in node.names)
        elif isinstance(node,ast.ImportFrom):imports.append(node.module or '')
    assert all(name.split('.')[0] in {'hashlib','json','re','functools','bnbagent','eth_abi','eth_utils'} for name in imports)
    assert 'expected_contract_identity(' not in source and 'assess_envelope(' not in source
    assert 'corpus.json' not in source and 'responses.jsonl' not in source


def test_nearest_rank_p95_and_median_units():
    assert stats(list(range(1,21)))=={'samples':20,'median_us':.0105,'p95_us':.019}


def test_input_copy_and_mutation_detection():
    original={'input':[1]}
    def malicious(value,*,now):
        value['input'].append(2);return {'reason':'MUTATED'}
    result,elapsed,unchanged=_invoke(malicious,original,1000)
    assert unchanged is False and original=={'input':[1]} and elapsed>=0
    assert result['reason']=='MUTATED'


def test_exception_diagnostic_omits_raw_message():
    def broken(*_args,**_kwargs):raise ValueError('private content')
    result,_,unchanged=_invoke(broken,{},1000)
    assert result['reason']=='ASSESSMENT_EXCEPTION' and not unchanged
    assert 'private' not in json.dumps(result)


def test_baseline_authorization_cannot_grant_execution():
    case=next(c for c in CORPUS['cases'] if c['case_id']=='erc20.allowance/matched')
    package=strict_json(case['input_json']);c=package['claim']
    authorization={k:c[k] for k in ('predicate','chain_id','target','arguments')}
    authorization.update({'allowed_actions':['analyze'],'deadline':1100,'max_asset_spend':0})
    valid=assess_baseline(package,now=1000,authorization=authorization)
    assert valid['current_use_allowed'] and valid['execution_authorized'] is False
    authorization['max_asset_spend']=True
    assert assess_baseline(package,now=1000,authorization=authorization)['authorization_status']=='BLOCKED'


@pytest.mark.parametrize('field',['control_outcome_errors','unauthorized_current_use','false_acceptances','execution_grants'])
def test_safety_or_full_control_error_blocks_apparent_advantage(field):
    candidate={'control_outcome_errors':0,'unauthorized_current_use':0,'false_acceptances':0,'execution_grants':0}
    candidate[field]=1
    assert advantage_gates(['win1','win2','win3'],[],candidate,{'median_us':.5,'p95_us':.5})=={
        'correctness_advantage':False,'runtime_advantage':False}


def test_net_gain_and_runtime_regression_rules():
    candidate={'control_outcome_errors':0,'unauthorized_current_use':0,'false_acceptances':0,'execution_grants':0}
    assert advantage_gates(['win1'],[],candidate,{'median_us':1,'p95_us':1})['correctness_advantage'] is False
    result=advantage_gates(['win1','win2','win3'],['regression'],candidate,{'median_us':.5,'p95_us':.5})
    assert result['correctness_advantage'] is True and result['runtime_advantage'] is False


def test_boolean_outcomes_do_not_equal_integer_zero():
    assert same_outcomes({'execution_authorized':False},{'execution_authorized':False})
    assert not same_outcomes({'execution_authorized':0},{'execution_authorized':False})
