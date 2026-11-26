import pytest

from veriabstain_eval.deepseek_runtime import BudgetJournal, run_one, payload_for
from veriabstain_eval.workers import digest


def record(i=0):
    body = {'protocol_version': 1, 'messages': [{'role': 'system', 'content': 'Analyze'},
            {'role': 'user', 'content': 'data'}], 'response_schema': {'type': 'object'},
            'generation': {'temperature': 0, 'max_output_tokens': 512}}
    return {'request_id': str(i), 'request_digest': digest(body), 'request': body}


def response(*_):
    return {'model': 'provider-version', 'choices': [{'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': '{}'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 2}}


def test_persisted_results_not_called_twice(tmp_path):
    path = tmp_path / 'budget.db'
    journal = BudgetJournal(path)
    first = run_one(record(), journal, 'test-only', transport=response)
    journal.close()
    journal = BudgetJournal(path)
    try:
        assert run_one(record(), journal, 'test-only', transport=lambda *_: pytest.fail('Repeated call')) == first
    finally:
        journal.close()


def test_ambiguous_call_consumes_budget_and_blocks_retry(tmp_path):
    journal = BudgetJournal(tmp_path / 'budget.db')
    try:
        def failure(*_):
            raise TimeoutError('Ambiguous')
        with pytest.raises(TimeoutError):
            run_one(record(), journal, 'test-only', transport=failure)
        with pytest.raises(ValueError, match='Ambiguous'):
            run_one(record(), journal, 'test-only', transport=response)
        assert journal.db.execute('SELECT SUM(reservation) FROM calls').fetchone()[0] == 20_000
    finally:
        journal.close()


def test_cap_shared_across_connections(tmp_path):
    path = tmp_path / 'budget.db'
    a, b = BudgetJournal(path), BudgetJournal(path)
    try:
        for i in range(100):
            r = record(i)
            (a if i % 2 else b).reserve(r, payload_for(r))
        with pytest.raises(ValueError, match='exhausted'):
            a.reserve(record(101), payload_for(record(101)))
    finally:
        a.close()
        b.close()


def test_context_tampering_before_call(tmp_path):
    journal = BudgetJournal(tmp_path / 'budget.db')
    r = record()
    r['request']['messages'][0]['content'] = 'modified'
    try:
        with pytest.raises(ValueError, match='digest'):
            run_one(r, journal, 'test-only', transport=lambda *_: pytest.fail('Called'))
        assert journal.db.execute('SELECT COUNT(*) FROM calls').fetchone()[0] == 0
    finally:
        journal.close()
