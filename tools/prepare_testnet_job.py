"""Read BSC testnet state and prepare at most one unsigned job transaction.

Never loads keys, signs, broadcasts, or deploys. Exit codes: 0 valid plan or
confirmed funded state, 1 invalid input/RPC/output failure, 2 missing inputs or
blocked preflight. An unsigned plan is not a funded job or execution approval.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import ValidationError
from web3 import HTTPProvider, Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/evaluation"))
from veriabstain_eval.testnet_plan import TestnetJobSpec, build_testnet_plan
from veriabstain_eval.workers import strict_json


def _atomic_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            json.dump(report, output, indent=2, allow_nan=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _base_report(status):
    return {"status": status, "chain_id": 97, "read_only": True,
            "signatures_created": 0, "transactions_broadcast": 0, "deployments": 0}


def _emit(report, output, *, error=False):
    if output is not None:
        _atomic_report(output, report)
    print(json.dumps(report, indent=2, allow_nan=False), file=sys.stderr if error else sys.stdout)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse may quote unknown arguments containing RPC credentials.
        # Emit a fixed usage error instead of echoing the command line.
        report = {**_base_report("NEEDS_INPUT"), "message": "Invalid command arguments; use --help for the public-input options."}
        print(json.dumps(report, indent=2), file=sys.stderr)
        self.exit(2)


def _load_spec(path):
    with path.open(encoding="utf-8") as source:
        raw = source.read(65_537)
    if len(raw.encode()) > 65_536:
        raise ValueError("Public job specification exceeds the size limit")
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise ValueError("Public job specification must be an object")
    return TestnetJobSpec.model_validate(value)


def _provider(rpc_url):
    parsed = urlsplit(rpc_url)
    if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.fragment:
        raise ValueError("Unsupported RPC URL")
    w3 = Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": 15}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def main(argv=None):
    parser = _SafeParser(description=__doc__)
    parser.add_argument("--schema", action="store_true", help="Show the public-input JSON Schema offline")
    parser.add_argument("--spec", type=Path, help="Reviewed public job specification JSON; no keys or sessions")
    parser.add_argument("--rpc-url", help="Explicit BSC testnet read-only RPC; never included in reports")
    parser.add_argument("--creation-tx-hash", help="Confirmed create-job transaction hash for the next stage")
    parser.add_argument("--output", type=Path, help="Report path; defaults to artifacts/testnet/plan.json for planning")
    args = parser.parse_args(argv)
    output = args.output if args.schema else (args.output or ROOT / "artifacts/testnet/plan.json")
    try:
        if args.schema:
            if args.spec is not None or args.rpc_url is not None or args.creation_tx_hash is not None:
                raise ValueError("Schema export cannot be combined with network planning")
            _emit({**_base_report("SPEC_SCHEMA"), "schema": TestnetJobSpec.model_json_schema()}, output)
            return 0
        missing = [name for name, value in (("spec", args.spec), ("rpc_url", args.rpc_url)) if not value]
        if missing:
            _emit({**_base_report("NEEDS_INPUT"), "missing": missing,
                   "message": "Supply a reviewed public job specification and explicit testnet RPC. No transaction has been prepared."}, output)
            return 2
        if args.spec.resolve() == output.resolve():
            output = None
            raise ValueError("The report must not overwrite its input specification")
        _atomic_report(output, _base_report("RUNNING"))
        if args.creation_tx_hash is not None and not re.fullmatch(r"0x[0-9a-fA-F]{64}", args.creation_tx_hash):
            raise ValueError("Invalid creation transaction hash")
        try:
            spec = _load_spec(args.spec)
        except ValidationError as error:
            missing_fields = sorted({item["loc"][0] for item in error.errors(include_input=False)
                                     if item["type"] == "missing" and item["loc"]
                                     and item["loc"][0] in TestnetJobSpec.model_fields})
            if missing_fields:
                _emit({**_base_report("NEEDS_INPUT"), "missing": missing_fields,
                       "message": "The public job specification is incomplete. Client and provider must be explicitly supplied; no roles are inferred."}, output)
                return 2
            raise
        report = build_testnet_plan(_provider(args.rpc_url), spec, creation_tx_hash=args.creation_tx_hash)
        if report.get("status") not in ("UNSIGNED_PLAN", "BLOCKED", "FUNDED_CONFIRMED"):
            raise ValueError("Unexpected testnet planning status")
        if report["status"] == "BLOCKED" and report.get("next_transaction") is not None:
            raise ValueError("Blocked preparation cannot include a transaction")
        report = {**report, **_base_report(report["status"])}
        _emit(report, output)
        return 2 if report["status"] == "BLOCKED" else 0
    except Exception as error:
        report = {**_base_report("ERROR"), "error_type": type(error).__name__,
                  "message": "Testnet preparation failed. Check public inputs, authenticated quote, deployment context, and RPC availability; no transaction was signed or broadcast."}
        try:
            _emit(report, output, error=True)
        except (OSError, ValueError):
            print(json.dumps(report, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
