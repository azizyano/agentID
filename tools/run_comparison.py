"""Export pending comparison requests or import recorded replies; never run a model.

Exit codes: 0 completed replay, 1 input/state/output error, 2 awaiting responses.
"""

import argparse
import asyncio
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/evaluation"))
from veriabstain_eval.comparison import run_comparison
from veriabstain_eval.workers import ResponseFileWorker


def _atomic_write(path, text):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _jsonl(records):
    return "".join(json.dumps(record, sort_keys=True, allow_nan=False) + "\n" for record in records)


def _publish(output, summary, requests, results):
    # summary.json is the commit marker. RUNNING remains visible until all
    # current artifacts have replaced the previous ones successfully.
    _atomic_write(output / "requests.jsonl", _jsonl(requests))
    _atomic_write(output / "results.jsonl", _jsonl(results))
    _atomic_write(output / "summary.json", json.dumps(summary, indent=2, allow_nan=False) + "\n")


def _error_summary(run_id, error):
    if isinstance(error, (ValueError, sqlite3.Error, UnicodeError)):
        message = "Comparison input or saved state is invalid; check the response file and run context."
    elif isinstance(error, OSError):
        message = "Could not read or write the local comparison files."
    else:
        message = "The comparison could not finish; current exports are unavailable."
    return {"run_id": run_id, "run_status": "ERROR", "artifacts_complete": False,
            "mode": "FIXTURE_REPLAY_UNATTESTED", "behavioral_proof": "BLOCKED",
            "incremental_value_over_C": "UNPROVEN", "error_type": type(error).__name__,
            "message": message, "model_calls": 0, "transactions": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--responses", type=Path, help="Import recorded JSONL replies without invoking a model")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/g1b")
    parser.add_argument("--run-id", default="g1b-v1")
    args = parser.parse_args(argv)
    output_ready = False
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", args.run_id):
            raise ValueError("Invalid experiment run ID")
        args.output.mkdir(parents=True, exist_ok=True)
        # Revoke the old success marker before any import or database mutation.
        _atomic_write(args.output / "summary.json", json.dumps({
            "run_id": args.run_id, "run_status": "RUNNING", "artifacts_complete": False,
            "mode": "FIXTURE_REPLAY_UNATTESTED", "behavioral_proof": "BLOCKED",
        }, indent=2) + "\n")
        output_ready = True
        worker = ResponseFileWorker(args.responses)
        summary, results = asyncio.run(run_comparison(
            worker, args.output / "comparison.sqlite3", args.run_id,
        ))
        requests, observed_request_ids, exported_results = [], set(), []
        for result in results:
            result = dict(result)
            history = result.pop("requests")
            result["request_ids"] = [request["request_id"] for request in history]
            observed_request_ids.update(result["request_ids"])
            requests.extend(request for request in history if request["state"] == "AWAITING_RESPONSE")
            exported_results.append(result)
        imported_ids = set(worker.responses)
        unmatched = imported_ids - observed_request_ids
        if unmatched:
            raise ValueError("The response file contains IDs not requested by this run")
        summary = {**summary,
                   "run_status": "AWAITING_RESPONSES" if requests else "COMPLETED_REPLAY",
                   "artifacts_complete": True,
                   "pending_requests": len(requests),
                   "response_import": {"provided": len(imported_ids),
                                       "matched": len(imported_ids), "unmatched": 0}}
        _publish(args.output, summary, requests, exported_results)
        print(json.dumps(summary, indent=2, allow_nan=False))
        return 2 if requests else 0
    except Exception as error:
        summary = _error_summary(args.run_id, error)
        if output_ready:
            try:
                # Clear generated exports only, preserving the SQLite ledger.
                # A failed import may already have recorded some valid replies.
                _atomic_write(args.output / "summary.json", json.dumps(summary, indent=2) + "\n")
                _atomic_write(args.output / "requests.jsonl", "")
                _atomic_write(args.output / "results.jsonl", "")
            except OSError:
                summary["message"] += " The error report could not be fully written."
        print(json.dumps(summary, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
