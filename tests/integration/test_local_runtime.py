import copy

import pytest

from veriabstain_eval.local_runtime import chat_payload, generate
from veriabstain_eval.workers import digest


def request():
    body = {'protocol_version': 1,
            'messages': [{'role': 'system', 'content': 'Analyze only'},
                         {'role': 'user', 'content': 'untrusted data'}],
            'generation': {'temperature': 0, 'max_output_tokens': 512},
            'response_schema': {'type': 'object'}}
    return {'request_id': 'case1', 'request_digest': digest(body), 'request': body}


def response():
    return {'model': 'test:local', 'done': True, 'done_reason': 'stop',
            'message': {'role': 'assistant', 'content': 'invalid decision preserved'},
            'eval_count': 4}


def test_exact_binding_and_preserved_output():
    calls = []
    def transport(payload):
        calls.append(payload)
        return response()
    reply, metadata = generate(request(), 'test:local', transport=transport)
    assert reply['request_digest'] == request()['request_digest']
    assert reply['output'] == 'invalid decision preserved'
    assert metadata['eval_count'] == 4 and metadata['source'] == 'RUNTIME_SELF_REPORTED'
    assert calls == [{'model': 'test:local', 'messages': request()['request']['messages'],
                      'format': {'type': 'object'}, 'stream': False,
                      'options': {'temperature': 0, 'num_predict': 512}}]


def test_tampering_never_calls_runtime():
    record = request()
    record['request']['messages'][1]['content'] = 'changed'
    with pytest.raises(ValueError, match='digest'):
        generate(record, 'test:local', transport=lambda _: pytest.fail('Runtime called'))


@pytest.mark.parametrize('model', ['', 'model:cloud', 'https://service?secret=x'])
def test_disallowed_model(model):
    with pytest.raises(ValueError):
        chat_payload(request(), model)


@pytest.mark.parametrize('change', [
    {'done': False}, {'done_reason': 'length'}, {'model': 'different'},
    {'error': 'failure'}, {'eval_count': True},
    {'message': {'role': 'assistant', 'content': 'x', 'tool_calls': [{}]}},
])
def test_bad_responses_fail_without_retry(change):
    calls = []
    def transport(payload):
        calls.append(payload)
        return {**copy.deepcopy(response()), **change}
    with pytest.raises(ValueError):
        generate(request(), 'test:local', transport=transport)
    assert len(calls) == 1
