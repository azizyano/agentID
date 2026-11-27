import json
import runpy
from pathlib import Path

import pytest
from pydantic import ValidationError

from veriabstain_eval.wallet_compatibility import (
    CompatibilityCase,
    PreviewReportCase,
    check_compatibility,
    compare_compatibility,
)

ROOT = Path(__file__).resolve().parents[2]
ENTRY = runpy.run_path(str(ROOT / "tools/veriabstain.py"))
EXAMPLES = ROOT / "examples/wallet-compatibility"
NOW = 1795724500


def evaluate(example="receipt-preview-matched", *, observation=None, expected=None, now=NOW):
    payload = json.loads((EXAMPLES / f"{example}.json").read_text(encoding="utf-8"))
    payload["observation"].update(observation or {})
    payload["expected"].update(expected or {})
    return check_compatibility(CompatibilityCase.model_validate(payload), now)


def test_matching_preview_preserves_fixture_and_execution_boundaries():
    report = evaluate()
    assert report["status"] == "PREVIEW_MATCHED"
    assert report["evidence"] == "FIXTURE"
    assert report["reported_stage"] == "preview_passed"
    assert report["checks"]["wallet_fee"] == report["checks"]["app_confirmation"] == "MATCH"
    assert report["execution_authorized"] is report["submission_verified"] is False


def test_browser_wallet_mismatch_is_detected_before_preview():
    report = evaluate("receipt-wrong-wallet", observation={"native_value_wei": 20})
    assert report["status"] == "INCOMPATIBLE"
    assert report["checks"]["sender"] == "MISMATCH"
    assert report["checks"]["simulation"] == report["checks"]["native_value_wei"] == "UNKNOWN"


def test_successful_preview_can_still_miss_wallet_review_requirements():
    report = evaluate("receipt-preview-limited")
    assert report["status"] == "INCOMPATIBLE"
    assert report["checks"]["simulation"] == "PASSED"
    assert report["checks"]["calldata"] == "MATCH"
    assert report["checks"]["wallet_fee"] == "UNKNOWN"
    assert report["checks"]["app_confirmation"] == "MISMATCH"


@pytest.mark.parametrize(("field", "value"), [
    ("sender", "0x" + "22" * 20),
    ("chain_id", 97),
    ("target", "0x" + "22" * 20),
    ("calldata", "0x5475b0b4" + "ab" * 64),
    ("native_value_wei", 1),
])
def test_exact_action_mismatches_are_not_hidden_by_successful_simulation(field, value):
    report = evaluate(observation={field: value})
    assert report["status"] == "INCOMPATIBLE"
    assert report["checks"][field] == "MISMATCH"
    assert report["checks"]["simulation"] == "PASSED"


def test_preview_on_a_different_surface_does_not_validate_the_expected_flow():
    report = evaluate(observation={"surface": "binance_agentic_cli"})
    assert report["status"] == "INCOMPATIBLE"
    assert report["checks"]["wallet_surface"] == "MISMATCH"


@pytest.mark.parametrize(("observation", "field", "value"), [
    ({"observed_at": None}, "observation_age", "UNKNOWN"),
    ({"observed_at": NOW - 301}, "observation_age", "STALE"),
    ({"observed_at": NOW + 1}, "observation_age", "FUTURE"),
    ({"preview_expires_at": NOW}, "preview_expiry", "EXPIRED"),
    ({"preview_expires_at": None}, "preview_expiry", "UNKNOWN"),
    ({"wallet_fee_wei": None}, "wallet_fee", "UNKNOWN"),
    ({"app_confirmation_required": None}, "app_confirmation", "UNKNOWN"),
    ({"calldata": None}, "calldata", "UNKNOWN"),
    ({"risk_findings": "warning"}, "risk_review", "WARNING"),
    ({"risk_findings": None}, "risk_review", "UNKNOWN"),
    ({"surface": "unknown"}, "wallet_surface", "UNKNOWN"),
    ({"stage": "unknown"}, "simulation", "UNKNOWN"),
])
def test_incomplete_or_conflicting_evidence_is_inconclusive(observation, field, value):
    report = evaluate(observation=observation)
    assert report["status"] == "INCONCLUSIVE"
    assert report["checks"][field] == value


def test_blocked_preview_does_not_imply_simulation_or_authorization():
    report = evaluate(observation={"stage": "preview_blocked", "evidence": "USER_REPORTED"})
    assert report["status"] == "BLOCKED_BY_WALLET"
    assert report["evidence"] == "USER_REPORTED"
    assert report["checks"]["simulation"] == "UNKNOWN"
    assert report["execution_authorized"] is False


def test_optional_requirements_and_explicit_zero_fee():
    assert evaluate(observation={"wallet_fee_wei": 0})["checks"]["wallet_fee"] == "MATCH"
    report = evaluate(
        "receipt-preview-limited",
        expected={"requires_wallet_fee": False, "requires_app_confirmation": False},
    )
    assert report["status"] == "PREVIEW_MATCHED"
    assert report["checks"]["wallet_fee"] == report["checks"]["app_confirmation"] == "NOT_REQUIRED"


def test_partial_owner_preview_preserves_blockers_and_unknowns():
    payload = json.loads((EXAMPLES / "receipt-owner-preview.json").read_text(encoding="utf-8"))
    report = check_compatibility(PreviewReportCase.model_validate(payload), 1795724572)

    assert report["status"] == "INCONCLUSIVE"
    assert report["evidence"] == "USER_REPORTED"
    assert report["checks"]["wallet_fee"] == report["checks"]["app_confirmation"] == "MISMATCH"
    assert report["checks"]["observation_age"] == report["checks"]["calldata"] == "UNKNOWN"
    assert report["checks"]["sender"] == "UNKNOWN"
    assert report["checks"]["simulation"] == "PASSED"
    assert report["checks"]["preview_expiry"] == "EXPIRED"
    assert report["execution_authorized"] is report["submission_verified"] is False


@pytest.mark.parametrize(("displayed", "amount", "expected"), [
    (False, None, "MISMATCH"),
    (True, None, "UNKNOWN"),
    (None, None, "UNKNOWN"),
    (True, 0, "MATCH"),
])
def test_report_fee_distinguishes_display_from_known_amount(displayed, amount, expected):
    payload = json.loads((EXAMPLES / "receipt-preview-matched.json").read_text(encoding="utf-8"))
    payload["schema_version"] = 2
    payload["observation"].update(wallet_fee_displayed=displayed, wallet_fee_wei=amount)
    report = check_compatibility(PreviewReportCase.model_validate(payload), NOW)

    assert report["checks"]["wallet_fee"] == expected
    assert report["status"] == {
        "MISMATCH": "INCOMPATIBLE",
        "UNKNOWN": "INCONCLUSIVE",
        "MATCH": "PREVIEW_MATCHED",
    }[expected]


def test_report_rejects_conflicting_fee_evidence():
    payload = json.loads((EXAMPLES / "receipt-preview-matched.json").read_text(encoding="utf-8"))
    payload["schema_version"] = 2
    payload["observation"].update(wallet_fee_displayed=False, wallet_fee_wei=0)
    with pytest.raises(ValidationError):
        PreviewReportCase.model_validate(payload)


def test_v1_still_requires_exact_expected_calldata():
    payload = json.loads((EXAMPLES / "receipt-preview-matched.json").read_text(encoding="utf-8"))
    del payload["expected"]["calldata"]
    with pytest.raises(ValidationError):
        CompatibilityCase.model_validate(payload)


def test_report_rejects_an_expected_selector_that_conflicts_with_calldata():
    payload = json.loads((EXAMPLES / "receipt-preview-matched.json").read_text(encoding="utf-8"))
    payload["schema_version"] = 2
    payload["expected"]["function_selector"] = "0x00000000"
    with pytest.raises(ValidationError):
        PreviewReportCase.model_validate(payload)


@pytest.mark.parametrize("fields", [
    {"order_id": "sensitive"},
    {"stage": "finalized"},
    {"chain_id": 56.0},
    {"calldata": "0x5475b0b41"},
    {"native_value_wei": "0"},
    {"wallet_fee_wei": -1},
    {"app_confirmation_required": "true"},
])
def test_rejects_unsupported_or_ambiguous_observation_input(fields):
    with pytest.raises(ValidationError):
        evaluate(observation=fields)


@pytest.mark.parametrize(("filename", "expected_exit"), [
    ("receipt-preview-matched", 0),
    ("receipt-preview-limited", 1),
    ("receipt-wrong-wallet", 1),
])
def test_cli_can_run_each_documented_case(filename, expected_exit, capsys):
    assert ENTRY["main"]([
        "compat", "--case", str(EXAMPLES / f"{filename}.json"), "--now", str(NOW),
    ]) == expected_exit
    output = capsys.readouterr().out
    assert "0x5475b0b4" not in output
    assert json.loads(output)["execution_authorized"] is False


def test_cli_rejects_duplicate_fields_without_echoing_input(tmp_path, capsys):
    path = tmp_path / "case.json"
    path.write_text('{"schema_version":1,"schema_version":"sensitive"}', encoding="utf-8")
    assert ENTRY["main"](["compat", "--case", str(path), "--now", str(NOW)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"status": "INVALID_CASE"}


def test_markdown_export_omits_sender_and_calldata(capsys):
    path = EXAMPLES / "receipt-preview-matched.json"
    expected = json.loads(path.read_text(encoding="utf-8"))["expected"]
    assert ENTRY["main"](["compat", "--case", str(path), "--now", str(NOW), "--format", "markdown"]) == 0
    output = capsys.readouterr().out

    assert "# VeriAbstain compatibility report" in output
    assert expected["target"] in output
    assert expected["sender"] not in output
    assert expected["calldata"] not in output
    assert "Execution authorized: false. Submission verified: false." in output


def test_cli_exports_the_partial_owner_report(capsys):
    path = EXAMPLES / "receipt-owner-preview.json"
    assert ENTRY["main"](["compat", "--case", str(path), "--now", "1795724572", "--format", "markdown"]) == 1
    output = capsys.readouterr().out

    assert "`INCONCLUSIVE`" in output
    assert "`USER_REPORTED`" in output
    assert "selector `0x5475b0b4`" in output
    assert "| Exact calldata | `UNKNOWN` |" in output
    assert "2026-11-26T20:22:52+00:00" in output
    assert "The fee amount is unknown." in output
    assert "`requireConfirmation: false`" in output


def test_cli_compares_the_owner_attempts_without_claiming_a_complete_fix(capsys):
    assert ENTRY["main"]([
        "compat", "--baseline", str(EXAMPLES / "receipt-owner-developer-mode-off.json"),
        "--case", str(EXAMPLES / "receipt-owner-preview.json"),
        "--now", "1795724572", "--format", "markdown",
    ]) == 1
    output = capsys.readouterr().out
    assert "`USER_REPORTED`" in output
    assert "| Assessment | `INCONCLUSIVE` | `INCONCLUSIVE` |" in output
    assert "| Developer Mode | `DISABLED` | `ENABLED` |" in output
    assert "| Simulation | `UNKNOWN` | `PASSED` |" in output
    assert "| Wallet-displayed fee | `UNKNOWN` | `MISMATCH` |" in output
    assert "| Separate Binance App approval | `UNKNOWN` | `MISMATCH` |" in output
    assert "| Full calldata | `UNKNOWN` |" in output
    assert "Attempt order comes from the supplied cases." in output
    assert "Execution authorized: false. Submission verified: false." in output


def test_comparison_cli_reuses_exact_assessments_and_keeps_fixtures_labeled(capsys):
    baseline_path = EXAMPLES / "receipt-preview-limited.json"
    expected = json.loads(baseline_path.read_text(encoding="utf-8"))["expected"]
    assert ENTRY["main"]([
        "compat", "--baseline", str(baseline_path), "--baseline-now", str(NOW - 1),
        "--case", str(EXAMPLES / "receipt-preview-matched.json"), "--now", str(NOW),
    ]) == 0
    output = capsys.readouterr().out
    comparison = json.loads(output)
    assert comparison["before"]["status"] == "INCOMPATIBLE"
    assert comparison["after"]["status"] == "PREVIEW_MATCHED"
    assert comparison["before"]["evidence"] == comparison["after"]["evidence"] == "FIXTURE"
    assert comparison["before"]["evaluated_at"] == NOW - 1
    assert comparison["expected_input_checks"]["calldata"] == "MATCH"
    assert expected["sender"] not in output
    assert expected["calldata"] not in output


@pytest.mark.parametrize("expected_changes", [
    {"requires_app_confirmation": False},
    {"target": "0x" + "22" * 20},
    {"calldata": "0x5475b0b4" + "ab" * 64},
    {"sender": "0x" + "22" * 20},
])
def test_comparison_rejects_changes_to_the_known_action_or_policy(expected_changes):
    payload = json.loads((EXAMPLES / "receipt-preview-matched.json").read_text(encoding="utf-8"))
    baseline = CompatibilityCase.model_validate(payload)
    payload["expected"].update(expected_changes)
    current = CompatibilityCase.model_validate(payload)
    with pytest.raises(ValueError):
        compare_compatibility(baseline, current, baseline_now=NOW, current_now=NOW)


def test_comparison_rejects_mixed_evidence_classes(tmp_path, capsys):
    filename = EXAMPLES / "receipt-preview-matched.json"
    payload = json.loads(filename.read_text(encoding="utf-8"))
    payload["observation"]["evidence"] = "USER_REPORTED"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(payload), encoding="utf-8")
    assert ENTRY["main"](["compat", "--baseline", str(baseline), "--case", str(filename), "--now", str(NOW)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"status": "INVALID_COMPARISON"}


def test_comparison_rejects_reversed_reported_observation_times():
    payload = json.loads((EXAMPLES / "receipt-preview-matched.json").read_text(encoding="utf-8"))
    baseline = CompatibilityCase.model_validate(payload)
    payload["observation"]["observed_at"] -= 1
    current = CompatibilityCase.model_validate(payload)
    with pytest.raises(ValueError):
        compare_compatibility(baseline, current, baseline_now=NOW, current_now=NOW)
