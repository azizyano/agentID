"""Prepare or review a minimal, offline VeriAbstain wallet issue report."""

import argparse
import json
import sys
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from veriabstain_eval.workers import strict_json

AGENT_ID = "veriabstin.ai"
MAX_REPORT_BYTES = 4_096

PROMPT = f"""Prepare a VeriAbstain issue report for {AGENT_ID} using only what is already visible in this chat. Show me the report for review. Do not use wallet tools, contact anyone, open a link, retry, sign, or submit anything. Return one JSON object with exactly these fields:
feature: "connection", "contract_call", "message_signature", "transfer", "swap", "approval", or "unknown".
chain_id: 56 for BNB Smart Chain mainnet, or null if another chain or unknown.
stage: "preview_passed", "preview_blocked", "approval_pending", "broadcast_reported", or "unknown". Use only an explicitly observed result. A missing hash does not establish the stage.
error_code: the exact numeric error code as an integer, or null.
fee_shown: true if the wallet displayed a fee, false if it explicitly omitted it, otherwise null.
app_confirmation_required: the exact boolean from the preview's requireConfirmation, or null.
tx_hash: the full public BNB Smart Chain transaction hash if explicitly present and I asked to include it, otherwise null.
Use null or "unknown" when unsure. Exclude all other details, especially credentials, wallet addresses, session or pairing data, order or request IDs, raw logs and messages."""


class WalletReport(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    feature: Literal["connection", "contract_call", "message_signature", "transfer", "swap", "approval", "unknown"]
    chain_id: Literal[56] | None
    stage: Literal["preview_passed", "preview_blocked", "approval_pending", "broadcast_reported", "unknown"]
    error_code: Annotated[int, Field(ge=1, le=99_999_999)] | None
    fee_shown: bool | None
    app_confirmation_required: bool | None
    tx_hash: Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{64}$")] | None


STAGE_NOTES = {
    "preview_passed": "The reported preview succeeded. A preview alone does not establish submission.",
    "preview_blocked": "The reported preview was blocked. Preserve the wallet's decision.",
    "approval_pending": "The wallet reportedly returned an approval request. Its current status is unverified.",
    "broadcast_reported": "The wallet reportedly broadcast a transaction. Its chain outcome is unverified.",
    "unknown": "The latest stage could not be determined from the report.",
}
BLOCKED_ERROR_NOTES = {
    ("contract_call", 351803): "Binance reported a risk block. The code alone does not identify its cause.",
    ("message_signature", 351817): "Binance reported that the requested signature type is unsupported.",
}


def review_report(path: Path):
    with path.open("rb") as source:
        raw = source.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("Report exceeds the size limit")
    report = WalletReport.model_validate(strict_json(raw.decode("utf-8")))
    if report.tx_hash is not None and report.chain_id != 56:
        raise ValueError("A transaction hash requires a known BSC chain")

    notes = [STAGE_NOTES[report.stage]]
    if report.stage == "preview_blocked":
        error_note = BLOCKED_ERROR_NOTES.get((report.feature, report.error_code))
        if error_note is not None:
            notes.append(error_note)
    if report.fee_shown is False:
        notes.append("The user reported that the wallet did not display a fee.")
    if report.stage == "preview_passed" and report.app_confirmation_required is False:
        notes.append("The preview did not require a separate Binance App confirmation.")
    if report.tx_hash is None:
        notes.append("No public transaction hash was supplied. Broadcast status cannot be inferred from that.")
    else:
        notes.append("A hash was supplied. Its chain outcome needs a separate check.")
    return {
        "status": "REVIEW_READY",
        "project_agent_id": AGENT_ID,
        "evidence": "USER_REPORTED",
        "report": report.model_dump(exclude={"tx_hash"}),
        "transaction_hash_supplied": report.tx_hash is not None,
        "notes": notes,
        "execution_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--prompt", action="store_true", help="Print the prompt to paste into the user's AI chat.")
    operation.add_argument("--report", type=Path, help="Review a JSON report file locally.")
    args = parser.parse_args()
    if args.prompt:
        print(PROMPT)
        return 0
    try:
        print(json.dumps(review_report(args.report), indent=2))
    except (OSError, ValueError):
        print(json.dumps({"status": "INVALID_REPORT"}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
