"""Run at most five approved DeepSeek requests; hidden key prompt, no key files."""
import argparse
import getpass
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/evaluation'))
from veriabstain_eval.workers import strict_json
from veriabstain_eval.deepseek_runtime import BudgetJournal, run_one, payload_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requests', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--limit', type=int, default=5, choices=range(1, 81))
    args = parser.parse_args()
    journal = None
    try:
        records = []
        with args.requests.open(encoding='utf-8') as source:
            for line in source:
                if len(line.encode()) > 131_072:
                    raise ValueError('Oversized request line')
                record = strict_json(line)
                payload_for(record)
                records.append(record)
                if len(records) == args.limit:
                    break
        if not records:
            raise ValueError('No requests')
        if not args.execute:
            print(json.dumps({'status': 'DRY_RUN', 'requests': len(records),
                              'maximum_new_reservation_usd': len(records)*0.02,
                              'aggregate_cap_usd': 2, 'model_calls': 0}))
            return 0
        print('Use a NEW key, not the revoked key pasted in chat. Input is hidden.')
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            api_key = getpass.getpass('New DeepSeek API key: ')
        if not api_key or '\n' in api_key or '\r' in api_key:
            raise ValueError('Invalid key')
        directory = ROOT / 'artifacts/private/deepseek'
        directory.mkdir(parents=True, exist_ok=True)
        journal = BudgetJournal(directory / 'budget.sqlite3')
        results = [run_one(record, journal, api_key) for record in records]
        # Cumulative export keeps earlier pilot/retry replies available to replay.
        export_responses(journal, directory / 'responses.jsonl')
        print(json.dumps({'status': 'BATCH_RECORDED', 'responses': len(results),
                          'output': 'artifacts/private/deepseek/responses.jsonl',
                          'behavioral_value': 'UNPROVEN'}))
        return 0
    except Exception:
        # Never echo exception text, HTTP bodies, headers or secret values.
        print('STOPPED: inspect local journal; no automatic retry. Credentials and provider errors withheld.',
              file=sys.stderr)
        return 1
    finally:
        if journal:
            journal.close()


def export_responses(journal, path):
    import os
    import tempfile
    rows = journal.db.execute("SELECT output FROM calls WHERE state='COMPLETE' ORDER BY id").fetchall()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False, suffix='.tmp') as target:
            temporary = Path(target.name)
            for row in rows:
                target.write(json.dumps(strict_json(row[0])['reply']) + '\n')
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
