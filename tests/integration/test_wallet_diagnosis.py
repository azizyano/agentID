import json
import runpy
from pathlib import Path

import pytest

ENTRY = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/veriabstain.py"))

PREVIEW = {
    "feature": "contract_call",
    "chain_id": 56,
    "stage": "preview_passed",
    "error_code": None,
    "fee_shown": False,
    "app_confirmation_required": False,
    "tx_hash": None,
}


def test_prompt_uses_agent_id_as_a_local_label(capsys):
    assert ENTRY["main"](["diagnose", "--prompt"]) == 0
    prompt = capsys.readouterr().out
    assert "veriabstin.ai" in prompt
    assert "using only what is already visible in this chat" in prompt
    assert "Do not use wallet tools, contact anyone" in prompt


def test_preview_report_preserves_evidence_limits(tmp_path, capsys):
    report = tmp_path / "wallet.json"
    report.write_text(json.dumps(PREVIEW), encoding="utf-8")
    assert ENTRY["main"](["diagnose", "--report", str(report)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["evidence"] == "USER_REPORTED"
    assert result["execution_authorized"] is False
    assert result["transaction_hash_supplied"] is False
    assert any("does not establish submission" in note for note in result["notes"])


def test_hash_is_not_included_in_shareable_output(tmp_path, capsys):
    report = tmp_path / "wallet.json"
    tx_hash = "0x" + "12" * 32
    report.write_text(json.dumps({**PREVIEW, "stage": "broadcast_reported", "tx_hash": tx_hash}))
    assert ENTRY["main"](["diagnose", "--report", str(report)]) == 0
    output = capsys.readouterr().out
    assert tx_hash not in output
    assert json.loads(output)["transaction_hash_supplied"] is True


def test_risk_rejection_does_not_claim_a_cause(tmp_path, capsys):
    report = tmp_path / "wallet.json"
    report.write_text(json.dumps({**PREVIEW, "stage": "preview_blocked", "error_code": 351803}))
    assert ENTRY["main"](["diagnose", "--report", str(report)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert any("does not identify its cause" in note for note in result["notes"])
    assert result["execution_authorized"] is False


@pytest.mark.parametrize("fields", [
    {"session": "sensitive-value"},
    {"stage": "safe_to_execute"},
    {"app_confirmation_required": "false"},
    {"chain_id": None, "tx_hash": "0x" + "12" * 32},
])
def test_rejects_extra_fields_and_unverified_values(tmp_path, capsys, fields):
    report = tmp_path / "wallet.json"
    report.write_text(json.dumps({**PREVIEW, **fields}), encoding="utf-8")
    assert ENTRY["main"](["diagnose", "--report", str(report)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"status": "INVALID_REPORT"}
