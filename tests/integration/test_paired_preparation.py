import json
import runpy
from pathlib import Path

from veriabstain_eval.dataset import load_manifest
from veriabstain_eval.deepseek_runtime import BudgetJournal

ROOT = Path(__file__).resolve().parents[2]


def test_selection_is_fixed_and_covers_conditions():
    select = runpy.run_path(str(ROOT/'tools/prepare_paired_comparison.py'))['select_cases']
    manifest, _ = load_manifest()
    cases = manifest['cases']
    selected = select(cases)
    assert len(selected) == len(set(selected)) == 16
    assert selected == select(list(reversed(cases)))
    subset = [c for c in cases if c['id'] in selected]
    assert {c['condition'] for c in subset} == {c['condition'] for c in cases}
    assert len({c['claim']['predicate'] for c in subset}) == 2


def test_export_preserves_all_completed_and_excludes_ambiguous(tmp_path):
    export = runpy.run_path(str(ROOT/'tools/run_deepseek_batch.py'))['export_responses']
    journal = BudgetJournal(tmp_path/'budget.db')
    try:
        for i, state in enumerate(['COMPLETE','RESERVED','COMPLETE']):
            reply = {'request_id':str(i),'request_digest':'bound','output':'{}'}
            journal.db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)',
                (str(i),'bound','payload',20000,state,json.dumps({'reply':reply}) if state=='COMPLETE' else None))
        journal.db.commit()
        path = tmp_path/'responses.jsonl'
        export(journal,path)
        assert [json.loads(line)['request_id'] for line in path.read_text().splitlines()] == ['0','2']
        export(journal,path)
        assert len(path.read_text().splitlines()) == 2
    finally:
        journal.close()
