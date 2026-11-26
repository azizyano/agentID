"""Export a public signing request or import its public signature; no wallet access."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/evaluation"))
from veriabstain_eval.job_quote import prepare_quote, import_signature, metamask_script
from veriabstain_eval.workers import strict_json
from veriabstain_eval.dataset import canonical


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signature-file", type=Path)
    parser.add_argument("--renew-expired-unsigned", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/testnet/quote")
    args = parser.parse_args(argv)
    proposal = strict_json((ROOT / "config/job-proposal.json").read_text())
    draft = strict_json((ROOT / "config/testnet-job.draft.json").read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    request_file = args.output / "request.json"
    signed_file = args.output / "signed-job.json"
    now = int(time.time())
    try:
        if args.signature_file:
            if args.renew_expired_unsigned or signed_file.exists():
                raise ValueError("A signed job already exists or conflicting mode was selected; reconcile first")
            raw = args.signature_file.read_text().strip()
            request = strict_json(request_file.read_text())
            signed = import_signature(request, raw, proposal, draft, now)
            with signed_file.open("x", encoding="utf-8") as target:
                json.dump(signed, target, indent=2)
                target.write("\n")
            print("Provider signature verified; signed-job.json saved. No transaction sent.")
            return 0
        if signed_file.exists():
            raise ValueError("A signed job already exists; reconcile before creating another quote")
        if request_file.exists():
            previous = strict_json(request_file.read_text())
            expected = prepare_quote(proposal, draft, previous["created_at"])
            if canonical(previous) != canonical(expected):
                raise ValueError("Existing request differs from approved scope; reconcile first")
            if now < previous["expires_at"]:
                print(json.dumps({"status": previous["status"], "retained_existing_request": True,
                                  "expires_at": previous["expires_at"], "transactions_sent": 0}))
                return 0
            if not args.renew_expired_unsigned:
                raise ValueError("Quote expired; use --renew-expired-unsigned only before signing or creating a job")
            history = args.output / "history"
            history.mkdir(exist_ok=True)
            archive = history / (str(previous["created_at"]) + ".json")
            with archive.open("x", encoding="utf-8") as target:
                json.dump(previous, target, indent=2)
                target.write("\n")
        request = prepare_quote(proposal, draft, now)
        request_file.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
        (args.output / "message.txt").write_text(request["message_to_sign"] + "\n", encoding="utf-8")
        (args.output / "metamask-sign.js").write_text(metamask_script(request), encoding="utf-8")
        print(json.dumps({"status": request["status"], "provider": request["spec"]["provider"],
                          "budget_u": "1", "quote_valid_seconds": 900,
                          "expires_at": request["expires_at"], "transactions_sent": 0}, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({"status": "BLOCKED", "message": str(error), "transactions_sent": 0}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
