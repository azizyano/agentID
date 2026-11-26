"""DeepSeek transport with conservative, durable $2 experiment reservations.

No automatic retries. Every attempted call consumes $0.02 of the local budget,
including errors and ambiguous effects. Prices must be reviewed before running.
"""
import sqlite3
import urllib.request

from .dataset import canonical
from .local_runtime import chat_payload
from .workers import strict_json, digest

MODEL = 'deepseek-flash'
ENDPOINT = 'https://api.deepseek.com/chat/completions'
CAP_MICRO_USD = 2_000_000
RESERVE_MICRO_USD = 20_000


def payload_for(record):
    # Reuse exact protocol/digest validation; no Ollama network call occurs.
    validated = chat_payload(record, MODEL)
    messages = [dict(message) for message in validated['messages']]
    messages[0]['content'] += '\nReturn JSON matching this schema: ' + canonical(validated['format'])
    payload = {'model': MODEL, 'messages': messages, 'stream': False,
               'temperature': 0, 'max_tokens': 512, 'thinking': {'type': 'disabled'},
               'response_format': {'type': 'json_object'}}
    # UTF-8 byte bound plus 4096 token overhead is conservatively below $0.02
    # at reviewed peak $0.30/M input and $1.20/M output. Not a provider billing cap.
    if len(canonical(payload).encode()) > 16_384:
        raise ValueError('Request exceeds reviewed cost bound')
    return payload


class BudgetJournal:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute('CREATE TABLE IF NOT EXISTS calls '
                        '(id TEXT PRIMARY KEY,digest TEXT NOT NULL,payload_digest TEXT NOT NULL,'
                        'reservation INTEGER NOT NULL,state TEXT NOT NULL,output TEXT)')
        self.db.commit()

    def close(self):
        self.db.close()

    def reserve(self, record, payload):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            previous = self.db.execute('SELECT digest,payload_digest,state,output FROM calls WHERE id=?',
                                       (record['request_id'],)).fetchone()
            if previous:
                if previous[:2] != (record['request_digest'], digest(payload)):
                    raise ValueError('Saved request context differs')
                if previous[2] != 'COMPLETE':
                    raise ValueError('Ambiguous or failed prior call; no automatic retry')
                self.db.commit()
                return strict_json(previous[3])
            used = self.db.execute('SELECT COALESCE(SUM(reservation),0) FROM calls').fetchone()[0]
            if used + RESERVE_MICRO_USD > CAP_MICRO_USD:
                raise ValueError('$2 reservation budget exhausted')
            self.db.execute('INSERT INTO calls VALUES (?,?,?,?,?,NULL)',
                            (record['request_id'], record['request_digest'], digest(payload),
                             RESERVE_MICRO_USD, 'RESERVED'))
            self.db.commit()
            return None
        except Exception:
            self.db.rollback()
            raise

    def complete(self, record, result):
        cursor = self.db.execute("UPDATE calls SET state='COMPLETE',output=? WHERE id=? AND state='RESERVED'",
                                 (canonical(result), record['request_id']))
        if cursor.rowcount != 1:
            self.db.rollback()
            raise ValueError('Lost call reservation')
        self.db.commit()


def post(payload, api_key):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise ValueError('Redirect forbidden')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(ENDPOINT, canonical(payload).encode(),
                                     headers={'Authorization': 'Bearer ' + api_key,
                                              'Content-Type': 'application/json'}, method='POST')
    with opener.open(request, timeout=60) as response:
        raw = response.read(65_537)
    if len(raw) > 65_536:
        raise ValueError('Response too large')
    return strict_json(raw.decode('utf-8'))


def run_one(record, journal, api_key, *, transport=post):
    payload = payload_for(record)
    cached = journal.reserve(record, payload)
    if cached is not None:
        return cached
    # Any exception leaves the reservation consumed and blocks another call.
    response = transport(payload, api_key)
    choices = response.get('choices', [])
    if len(choices) != 1 or choices[0].get('finish_reason') != 'stop':
        raise ValueError('Failed or truncated response')
    message = choices[0]['message']
    if (message.get('role') != 'assistant' or message.get('tool_calls')
            or not isinstance(message.get('content'), str)
            or len(message['content'].encode()) > 16_384):
        raise ValueError('Invalid assistant output')
    usage = response.get('usage', {})
    if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ('prompt_tokens', 'completion_tokens')):
        raise ValueError('Missing usage accounting')
    if usage['completion_tokens'] > 512 or usage['prompt_tokens'] > 20_480:
        raise ValueError('Usage exceeds reviewed bound; stop and reconcile billing')
    result = {'reply': {'request_id': record['request_id'], 'request_digest': record['request_digest'],
                        'output': message['content']},
              'metadata': {'provider': 'deepseek', 'requested_model': MODEL,
                           'reported_model': response.get('model'), 'usage': {
                               k: usage[k] for k in ('prompt_tokens', 'completion_tokens')},
                           'payload_digest': digest(payload), 'reservation_micro_usd': RESERVE_MICRO_USD,
                           'provenance': 'PROVIDER_REPORTED', 'prices_reviewed': '2026-11-20'}}
    journal.complete(record, result)
    return result
