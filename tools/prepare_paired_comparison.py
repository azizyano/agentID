"""Freeze a small exploratory paired plan from existing requests, no inference."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/evaluation'))
from veriabstain_eval.dataset import load_manifest
from veriabstain_eval.workers import digest
from veriabstain_eval.deepseek_runtime import payload_for


def select_cases(cases):
    # Fixed condition/ID order only, never model outputs or evaluator scores.
    groups = {}
    for case in cases:
        groups.setdefault(case['condition'], []).append(case)
    selected = []
    for index, condition in enumerate(sorted(groups)):
        candidates = sorted(groups[condition], key=lambda c: c['id'])
        predicate = 'erc20.allowance' if index % 2 == 0 else 'erc8183.job_status'
        selected.append(next(c for c in candidates if c['claim']['predicate'] == predicate))
    for case in sorted(cases, key=lambda c: c['id']):
        if len(selected) == 16:
            break
        if case['id'].endswith('/1') and case['id'] not in {c['id'] for c in selected}:
            selected.append(case)
    return sorted(c['id'] for c in selected)


def main():
    manifest, _ = load_manifest()
    ids = select_cases(manifest['cases'])
    results = [json.loads(line) for line in (ROOT/'artifacts/g1b/results.jsonl').read_text().splitlines()]
    db = sqlite3.connect(f"file:{(ROOT/'artifacts/g1b/comparison.sqlite3').as_posix()}?mode=ro", uri=True)
    records = []
    for result in results:
        if result['id'] in ids and result['arm'] in ('C','C_RETRY','D'):
            for request_id in result['request_ids']:
                row = db.execute('SELECT payload FROM requests WHERE request_id=? AND round_number=0',
                                 (request_id,)).fetchone()
                if row:
                    record = json.loads(row[0])
                    payload_for(record)
                    records.append(record)
    db.close()
    if len(records) != 48 or len({r['request_id'] for r in records}) != 48:
        raise ValueError('Expected sixteen complete three-arm pairs')
    plan = {'version':1,'run_id':'g1b-v1','scope':'EXPLORATORY_SUBSET_NOT_G1_GATE',
            'selection':'Sorted condition, alternating predicate, then sorted missing replica1 until16; no outcome selection',
            'case_ids':ids,'arms':['C','C_RETRY','D'],'first_round_requests':48,
            'maximum_additional_retry_requests':32,'maximum_reservation_usd':1.60,
            'shared_total_cap_usd':2,'prompt_protocol':1,'records_digest':digest(records),
            'limitations':'Pilot outcomes already inspected; exploratory plan frozen before these paired calls. Reuse existing results, no replacement. Full40scenario/three-repetition gate remains pending.'}
    directory = ROOT/'artifacts/private/deepseek'
    directory.mkdir(parents=True, exist_ok=True)
    file = directory/'paired-plan.json'
    if file.exists() and json.loads(file.read_text()) != plan:
        raise ValueError('Existing paired plan differs; preserve and review')
    file.write_text(json.dumps(plan,indent=2)+'\n')
    (directory/'paired-requests.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    print(json.dumps({'status':'PAIRED_PLAN_READY','cases':16,'first_round_requests':48,
                      'maximum_reservation_usd':1.60,'model_calls':0}))


if __name__ == '__main__':
    main()
