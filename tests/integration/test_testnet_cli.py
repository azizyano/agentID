"""Read-only unsigned planner CLI behavior; no RPC connections are made."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/prepare_testnet_job.py"


@pytest.fixture
def cli():
    spec = importlib.util.spec_from_file_location("testnet_cli_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def public_spec():
    from veriabstain_eval.testnet_plan import PINNED
    return {"chain_id": 97, "client": "0x" + "11" * 20, "provider": "0x" + "22" * 20,
            "commerce": PINNED.commerce_proxy, "router": PINNED.router_proxy,
            "policy": PINNED.policy, "payment_token": PINNED.payment_token,
            "budget": 1000, "expired_at": 2_000_000_000, "quote": {}}


def test_schema_export_is_offline_and_creates_no_plan_by_default(cli, monkeypatch, capsys):
    provider = Mock(side_effect=AssertionError("Schema export must stay offline"))
    monkeypatch.setattr(cli, "_provider", provider)
    assert cli.main(["--schema"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "SPEC_SCHEMA"
    assert report["chain_id"] == 97
    assert report["schema"]["properties"]["chain_id"]["const"] == 97
    assert {"client", "provider", "quote"}.issubset(report["schema"]["required"])
    provider.assert_not_called()


def test_missing_inputs_report_needs_input_without_network(cli, monkeypatch, tmp_path, capsys):
    provider = Mock(side_effect=AssertionError("Missing inputs must not use RPC"))
    monkeypatch.setattr(cli, "_provider", provider)
    output = tmp_path / "plan.json"
    assert cli.main(["--output", str(output)]) == 2
    report = json.loads(output.read_text())
    assert report["status"] == "NEEDS_INPUT"
    assert report["missing"] == ["spec", "rpc_url"]
    assert report["transactions_broadcast"] == report["signatures_created"] == 0
    provider.assert_not_called()


def test_report_cannot_overwrite_reviewed_spec(cli, monkeypatch, tmp_path):
    source = tmp_path / "spec.json"
    original = json.dumps(public_spec())
    source.write_text(original)
    provider = Mock(side_effect=AssertionError("Conflicting paths must stay offline"))
    monkeypatch.setattr(cli, "_provider", provider)
    assert cli.main(["--spec", str(source), "--rpc-url", "https://rpc.invalid", "--output", str(source)]) == 1
    assert source.read_text() == original
    provider.assert_not_called()


def test_missing_provider_does_not_reuse_client(cli, monkeypatch, tmp_path):
    data = public_spec()
    del data["provider"]
    source = tmp_path / "spec.json"
    source.write_text(json.dumps(data))
    provider = Mock(side_effect=AssertionError("Incomplete input must not use RPC"))
    monkeypatch.setattr(cli, "_provider", provider)
    output = tmp_path / "plan.json"
    assert cli.main(["--spec", str(source), "--rpc-url", "https://rpc.invalid", "--output", str(output)]) == 2
    report = json.loads(output.read_text())
    assert report["missing"] == ["provider"]
    provider.assert_not_called()


@pytest.mark.parametrize("status", ["UNSIGNED_PLAN", "FUNDED_CONFIRMED"])
def test_valid_report_preserves_unsigned_or_confirmed_status(cli, monkeypatch, tmp_path, status):
    source = tmp_path / "spec.json"
    source.write_text(json.dumps(public_spec()))
    w3 = object()
    provider = Mock(return_value=w3)
    monkeypatch.setattr(cli, "_provider", provider)
    planner = Mock(return_value={"status": status, "stage": "CREATE_JOB" if status == "UNSIGNED_PLAN" else status,
                                 "next_transaction": {"to": "0x" + "33" * 20, "data": "0x1234"} if status == "UNSIGNED_PLAN" else None})
    monkeypatch.setattr(cli, "build_testnet_plan", planner)
    output = tmp_path / "plan.json"
    transaction_hash = "0x" + "ab" * 32
    assert cli.main(["--spec", str(source), "--rpc-url", "https://rpc.invalid/SECRET", "--creation-tx-hash", transaction_hash,
                     "--output", str(output)]) == 0
    report = json.loads(output.read_text())
    assert report["status"] == status
    assert report["chain_id"] == 97
    assert report["read_only"] is True
    assert report["transactions_broadcast"] == report["signatures_created"] == report["deployments"] == 0
    assert "SECRET" not in output.read_text()
    assert planner.call_args.kwargs["creation_tx_hash"] == transaction_hash
    assert planner.call_args.args[0] is w3


@pytest.mark.parametrize("change", ["mainnet", "malformed", "duplicate_field", "extra_secret", "bad_hash"])
def test_invalid_inputs_do_not_connect_or_leave_previous_ready_report(cli, monkeypatch, tmp_path, change):
    data = public_spec()
    if change == "mainnet":
        data["chain_id"] = 56
    elif change == "extra_secret":
        data["private_key"] = "DO_NOT_PRINT"
    raw = json.dumps(data)
    if change == "malformed":
        raw = "not-json"
    elif change == "duplicate_field":
        raw = '{"chain_id":97,"chain_id":56}'
    source = tmp_path / "spec.json"
    source.write_text(raw)
    output = tmp_path / "plan.json"
    output.write_text('{"status":"UNSIGNED_PLAN"}')
    provider = Mock(side_effect=AssertionError("Invalid input must not use RPC"))
    monkeypatch.setattr(cli, "_provider", provider)
    args = ["--spec", str(source), "--rpc-url", "https://rpc.invalid", "--output", str(output)]
    if change == "bad_hash":
        args.extend(["--creation-tx-hash", "bad"])
    assert cli.main(args) == 1
    report = json.loads(output.read_text())
    assert report["status"] == "ERROR"
    assert "DO_NOT_PRINT" not in output.read_text()
    provider.assert_not_called()


def test_rpc_error_redacts_endpoint_from_stderr_and_report(cli, monkeypatch, tmp_path, capsys):
    source = tmp_path / "spec.json"
    source.write_text(json.dumps(public_spec()))
    secret_url = "https://rpc.invalid/SECRET_TOKEN"
    monkeypatch.setattr(cli, "_provider", Mock(side_effect=RuntimeError(f"Failed RPC {secret_url}")))
    output = tmp_path / "plan.json"
    assert cli.main(["--spec", str(source), "--rpc-url", secret_url, "--output", str(output)]) == 1
    assert "SECRET_TOKEN" not in capsys.readouterr().err
    assert "SECRET_TOKEN" not in output.read_text()
    assert json.loads(output.read_text())["status"] == "ERROR"


def test_implementation_drift_is_explicitly_blocked_without_unsigned_transaction(cli, monkeypatch, tmp_path):
    source = tmp_path / "spec.json"
    source.write_text(json.dumps(public_spec()))
    monkeypatch.setattr(cli, "_provider", Mock(return_value=object()))
    monkeypatch.setattr(cli, "build_testnet_plan", Mock(return_value={
        "status": "BLOCKED", "stage": "PREFLIGHT", "next_transaction": None,
        "blockers": ["IMPLEMENTATION_DRIFT"],
    }))
    output = tmp_path / "plan.json"
    assert cli.main(["--spec", str(source), "--rpc-url", "https://rpc.invalid", "--output", str(output)]) == 2
    report = json.loads(output.read_text())
    assert report["status"] == "BLOCKED"
    assert report["blockers"] == ["IMPLEMENTATION_DRIFT"]
    assert report["next_transaction"] is None


def test_blocked_report_must_not_smuggle_transaction(cli, monkeypatch, tmp_path):
    source = tmp_path / "spec.json"
    source.write_text(json.dumps(public_spec()))
    monkeypatch.setattr(cli, "_provider", Mock(return_value=object()))
    monkeypatch.setattr(cli, "build_testnet_plan", Mock(return_value={
        "status": "BLOCKED", "next_transaction": {"to": "unapproved"},
    }))
    output = tmp_path / "plan.json"
    assert cli.main(["--spec", str(source), "--rpc-url", "https://rpc.invalid", "--output", str(output)]) == 1
    assert json.loads(output.read_text())["status"] == "ERROR"


def test_unrecognized_arguments_never_echo_rpc_credentials(cli, capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["--wrong-option", "SECRET_RPC_TOKEN"])
    assert error.value.code == 2
    report = json.loads(capsys.readouterr().err)
    assert report["status"] == "NEEDS_INPUT"
    assert "SECRET_RPC_TOKEN" not in json.dumps(report)
