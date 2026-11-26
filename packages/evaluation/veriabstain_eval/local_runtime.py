"""Bounded Ollama transport adapter. Importing this module never calls a model.

Responses remain self-reported runtime observations, not model attestation.
The experiment runner must persist request state before invoking generate.
"""
import re
import urllib.request

from .dataset import canonical
from .workers import digest, strict_json

CHAT_URL = 'http://127.0.0.1:11434/api/chat'
MAX_RESPONSE_BYTES = 65_536


def chat_payload(record, model):
    if (not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}', model)
            or 'cloud' in model.lower()):
        raise ValueError('An explicit local model name is required; cloud models are excluded')
    body = record['request']
    if record['request_digest'] != digest(body) or body['protocol_version'] != 1:
        raise ValueError('Request digest or protocol mismatch')
    generation = body['generation']
    if generation != {'temperature': 0, 'max_output_tokens': 512}:
        raise ValueError('Unsupported generation settings')
    if (not isinstance(body['messages'], list) or len(body['messages']) != 2
            or [m.get('role') for m in body['messages']] != ['system', 'user']
            or any(set(m) != {'role', 'content'} or not isinstance(m['content'], str)
                   for m in body['messages'])):
        raise ValueError('Unsupported messages')
    if len(canonical(body).encode()) > 65_536:
        raise ValueError('Request exceeds local runtime input limit')
    return {'model': model, 'messages': body['messages'], 'format': body['response_schema'],
            'stream': False, 'options': {'temperature': 0, 'num_predict': 512}}


def local_post(payload):
    """One loopback request; no proxy, redirect, credentials, retries or model pull."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise ValueError('Runtime redirects are forbidden')

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(CHAT_URL, canonical(payload).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
    with opener.open(request, timeout=120) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('Runtime response exceeds limit')
    return strict_json(raw.decode('utf-8'))


def generate(record, model, *, transport=local_post):
    """Explicit single inference; caller owns consent, durable checkpoints and retries.

    A loopback server can itself forward to a remote service. Local model name
    validation alone cannot establish where inference actually executes.
    """
    payload = chat_payload(record, model)
    response = transport(payload)
    if (not isinstance(response, dict) or response.get('done') is not True
            or response.get('model') != model or response.get('error')
            or response.get('done_reason') != 'stop'):
        raise ValueError('Runtime failed, truncated output, or model mismatch')
    message = response.get('message')
    if (not isinstance(message, dict) or message.get('role') != 'assistant'
            or message.get('tool_calls') or not isinstance(message.get('content'), str)
            or len(message['content'].encode()) > 16_384):
        raise ValueError('Unsupported runtime message')
    # Preserve invalid decision JSON for the evaluator rather than repairing it.
    reply = {'request_id': record['request_id'], 'request_digest': record['request_digest'],
             'output': message['content']}
    metadata = {'runtime': 'ollama', 'model': model, 'model_calls': 1,
                'source': 'RUNTIME_SELF_REPORTED', 'request_digest': record['request_digest']}
    for key in ('prompt_eval_count', 'eval_count', 'total_duration'):
        value = response.get(key)
        if value is not None:
            if type(value) is not int or value < 0:
                raise ValueError('Invalid runtime metrics')
            metadata[key] = value
    return reply, metadata
