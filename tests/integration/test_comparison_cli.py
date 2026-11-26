"""CLI artifact/exit behavior, independent of the comparison scorer."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/run_comparison.py"
REQUEST_ID = "a" * 64
DIGEST = "b" * 64


@pytest.fixture
def cli():
    spec = importlib.util.spec_from_file_location("comparison_cli_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def returned_run(pending):
    summary = {"mode": "FIXTURE_REPLAY_UNATTESTED", "awaiting_response": int(pending),
               "behavioral_proof": "BLOCKED", "model_calls": 0, "transactions": 0}
    result = {"id": "case", "arm": "D", "status": "AWAITING_RESPONSE" if pending else "REFUSED",
              "requests": [{"request_id": REQUEST_ID, "request_digest": DIGEST,
                            "request": {}, "state": "AWAITING_RESPONSE" if pending else "RECORDED"}]}
    return summary, [result]


@pytest.mark.parametrize("pending,exit_code,status", [
    (True, 2, "AWAITING_RESPONSES"), (False, 0, "COMPLETED_REPLAY"),
])
def test_exit_code_and_artifacts_distinguish_pending_and_complete(cli, monkeypatch, tmp_path, capsys,
                                                                pending, exit_code, status):
    async def fake_run(*args):
        return returned_run(pending)

    monkeypatch.setattr(cli, "run_comparison", fake_run)
    assert cli.main(["--output", str(tmp_path), "--run-id", "test"]) == exit_code
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["run_status"] == status
    assert summary["artifacts_complete"] is True
    assert summary["pending_requests"] == int(pending)
    assert summary["response_import"] == {"provided": 0, "matched": 0, "unmatched": 0}
    requests = (tmp_path / "requests.jsonl").read_text().splitlines()
    assert len(requests) == int(pending)
    result = json.loads((tmp_path / "results.jsonl").read_text())
    assert result["request_ids"] == [REQUEST_ID]
    assert "requests" not in result
    assert status in capsys.readouterr().out


def test_failed_run_cannot_leave_previous_success_or_stale_exports(cli, monkeypatch, tmp_path, capsys):
    for name in ("summary.json", "requests.jsonl", "results.jsonl"):
        (tmp_path / name).write_text("old success")
    (tmp_path / "comparison.sqlite3").write_bytes(b"preserve ledger")

    async def failure(*args):
        assert json.loads((tmp_path / "summary.json").read_text())["run_status"] == "RUNNING"
        raise ValueError("private input must not be printed")

    monkeypatch.setattr(cli, "run_comparison", failure)
    assert cli.main(["--output", str(tmp_path)]) == 1
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["run_status"] == "ERROR"
    assert summary["artifacts_complete"] is False
    assert (tmp_path / "requests.jsonl").read_text() == ""
    assert (tmp_path / "results.jsonl").read_text() == ""
    assert (tmp_path / "comparison.sqlite3").read_bytes() == b"preserve ledger"
    assert "private input" not in capsys.readouterr().err


def test_malformed_response_import_is_error_without_calling_runner(cli, monkeypatch, tmp_path):
    file = tmp_path / "responses.jsonl"
    file.write_text("malformed JSON\n")

    async def forbidden(*args):
        pytest.fail("Malformed imports must be rejected before running comparison")

    monkeypatch.setattr(cli, "run_comparison", forbidden)
    assert cli.main(["--output", str(tmp_path / "output"), "--responses", str(file)]) == 1
    summary = json.loads((tmp_path / "output/summary.json").read_text())
    assert summary["run_status"] == "ERROR"


def test_unknown_response_ids_are_reported_as_error(cli, monkeypatch, tmp_path):
    file = tmp_path / "responses.jsonl"
    file.write_text(json.dumps({"request_id": "c" * 64, "request_digest": DIGEST, "output": "{}"}) + "\n")

    async def fake_run(*args):
        return returned_run(False)

    monkeypatch.setattr(cli, "run_comparison", fake_run)
    assert cli.main(["--output", str(tmp_path / "output"), "--responses", str(file)]) == 1
    assert json.loads((tmp_path / "output/summary.json").read_text())["run_status"] == "ERROR"


def test_completed_replay_reports_matched_import_count(cli, monkeypatch, tmp_path):
    file = tmp_path / "responses.jsonl"
    file.write_text(json.dumps({"request_id": REQUEST_ID, "request_digest": DIGEST, "output": "{}"}) + "\n")

    async def fake_run(*args):
        return returned_run(False)

    monkeypatch.setattr(cli, "run_comparison", fake_run)
    assert cli.main(["--output", str(tmp_path / "output"), "--responses", str(file)]) == 0
    summary = json.loads((tmp_path / "output/summary.json").read_text())
    assert summary["response_import"]["provided"] == summary["response_import"]["matched"] == 1


def test_invalid_run_id_does_not_touch_existing_artifacts(cli, tmp_path):
    (tmp_path / "summary.json").write_text("existing report")
    assert cli.main(["--output", str(tmp_path), "--run-id", "../wrong"]) == 1
    assert (tmp_path / "summary.json").read_text() == "existing report"


def test_atomic_write_failure_marks_run_error(cli, monkeypatch, tmp_path):
    original_write = cli._atomic_write

    def fail_results(path, text):
        if path.name == "results.jsonl":
            raise OSError("simulated disk failure")
        original_write(path, text)

    async def fake_run(*args):
        return returned_run(True)

    monkeypatch.setattr(cli, "run_comparison", fake_run)
    monkeypatch.setattr(cli, "_atomic_write", fail_results)
    assert cli.main(["--output", str(tmp_path)]) == 1
    # Error status is published before cleanup, so a cleanup failure still
    # cannot leave a previous COMPLETED marker on incomplete artifacts.
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["run_status"] == "ERROR"
    assert summary["artifacts_complete"] is False
