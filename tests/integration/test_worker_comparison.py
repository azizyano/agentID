import copy
import json

import pytest
from pydantic import ValidationError

from veriabstain_eval.comparison import compare_case
from veriabstain_eval.comparison_state import ComparisonState
from veriabstain_eval.dataset import load_manifest
from veriabstain_eval.runner import assess_reference
from veriabstain_eval.workers import (
    ARMS, ResponseFileWorker, make_request, parse_decision,
)

CASES, _ = load_manifest()


def case_for(condition):
    return copy.deepcopy(next(c for c in CASES["cases"] if c["condition"] == condition))


def answer(case, decision="COMPLETE", basis=None):
    return json.dumps({"decision": decision, "claim": case["claim"],
                       "observed_value": case["read"]["value"],
                       "warning_verdict": assess_reference(case["claim"], case["read"], case["now"]),
                       "refusal_basis": basis})


class ScriptedReplies:
    """Protocol test double. Never counted as a model or behavioral evidence."""
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.requests = []

    def lookup(self, request_id, request_digest):
        self.requests.append(request_id)
        return self.outputs.pop(0) if self.outputs else None


@pytest.fixture
def state(tmp_path):
    saved = ComparisonState(tmp_path / "state.sqlite3")
    yield saved
    saved.close()


@pytest.mark.parametrize("arm", ARMS)
def test_prompt_does_not_leak_condition_or_expected_answer(arm):
    case = case_for("false_warning")
    envelope = make_request(case, arm, 0, "test", verification="CONTRADICTED")
    messages = json.dumps(envelope["request"]["messages"])
    assert case["id"] not in messages
    assert case["operation_id"] not in messages
    assert "false_warning" not in messages
    assert "expected" not in messages
    payload = json.loads(envelope["request"]["messages"][1]["content"])
    assert ("trusted_direct_read" in payload) == (arm in ("C", "C_RETRY", "D"))


def test_c_and_d_receive_identical_authoritative_input_and_output_budgets():
    case = case_for("false_warning")
    requests = {arm: make_request(case, arm, 0, "test", verification="CONTRADICTED")["request"]
                for arm in ("C", "C_RETRY", "D")}
    payloads = {arm: json.loads(request["messages"][1]["content"]) for arm, request in requests.items()}
    assert payloads["C"] == payloads["C_RETRY"]
    payloads["D"].pop("typed_assessment")
    assert payloads["C"] == payloads["D"]
    assert requests["C"]["generation"] == requests["D"]["generation"]


@pytest.mark.parametrize("arm,condition,basis,rounds,accepted", [
    ("A", "false_warning", "FACTUAL_WARNING", 1, False),
    ("B", "false_warning", "FACTUAL_WARNING", 1, False),
    ("C", "false_warning", "FACTUAL_WARNING", 1, False),
    ("C_RETRY", "false_warning", "FACTUAL_WARNING", 2, True),
    ("D", "false_warning", "FACTUAL_WARNING", 2, True),
    ("D", "genuine_warning", "FACTUAL_WARNING", 1, False),
    ("D", "stale", "FACTUAL_WARNING", 1, False),
    ("D", "authorization_denied", "FACTUAL_WARNING", 1, False),
    ("D", "false_warning", "AUTHORIZATION", 1, False),
    ("D", "false_warning", "OTHER", 1, False),
])
async def test_reconsideration_is_bounded_and_preserves_independent_restrictions(
    state, arm, condition, basis, rounds, accepted,
):
    case = case_for(condition)
    worker = ScriptedReplies(answer(case, "REFUSE", basis), answer(case))
    result = await compare_case(case, arm, worker, state, "test")
    assert len(worker.requests) == rounds
    assert result["accepted_analysis"] is accepted
    assert result["simulated_effects"] == int(accepted)


async def test_d_cannot_override_refusal_about_a_different_claim(state):
    case = case_for("false_warning")
    output = json.loads(answer(case, "REFUSE", "FACTUAL_WARNING"))
    output["claim"]["arguments"]["spender"] = "0x" + "99" * 20
    worker = ScriptedReplies(json.dumps(output), answer(case))
    result = await compare_case(case, "D", worker, state, "test")
    assert len(worker.requests) == 1
    assert not result["accepted_analysis"]


@pytest.mark.parametrize("condition", ["false_warning", "genuine_warning", "authorization_denied", "provider_outage"])
async def test_task_specific_deliverable_acceptance(state, condition):
    case = case_for(condition)
    result = await compare_case(case, "D", ScriptedReplies(answer(case)), state, "test")
    assert result["accepted_analysis"] is (condition in ("false_warning", "genuine_warning"))


@pytest.mark.parametrize("change", ["wrong_value", "wrong_context", "extra_action", "boolean_amount", "malformed"])
async def test_unsafe_or_invalid_model_output_never_becomes_a_deliverable(state, change):
    case = case_for("false_warning")
    output = json.loads(answer(case))
    if change == "wrong_value":
        output["observed_value"] = 999999
    elif change == "wrong_context":
        output["claim"]["chain_id"] = 56
    elif change == "extra_action":
        output["transfer"] = "all funds"
    elif change == "boolean_amount":
        output["observed_value"] = True
    raw = "not-json" if change == "malformed" else json.dumps(output)
    result = await compare_case(case, "D", ScriptedReplies(raw), state, "test")
    assert result["simulated_effects"] == 0
    assert result["status"] in ("INVALID_OUTPUT", "REJECTED_DELIVERABLE")


async def test_retry_budget_and_pending_ids_survive_restart(tmp_path):
    path = tmp_path / "state.sqlite3"
    case = case_for("false_warning")
    first = ComparisonState(path)
    pending = await compare_case(case, "D", ScriptedReplies(), first, "test")
    first.close()
    second = ComparisonState(path)
    recovered = await compare_case(case, "D", ScriptedReplies(answer(case, "REFUSE", "FACTUAL_WARNING")), second, "test")
    second.close()
    assert recovered["requests"][0]["request_id"] == pending["requests"][0]["request_id"]
    third = ComparisonState(path)
    # The already-recorded first response is reused; the second stays pending.
    repeated = await compare_case(case, "D", ScriptedReplies(), third, "test")
    assert [r["request_id"] for r in repeated["requests"]] == [r["request_id"] for r in recovered["requests"]]
    assert len(repeated["requests"]) == 2
    assert repeated["requests"][0]["state"] == "RECORDED"
    assert repeated["requests"][1]["state"] == "AWAITING_RESPONSE"
    assert third.db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 2
    third.close()


async def test_reused_operation_rejects_changed_original_authorization(state):
    case = case_for("false_warning")
    await compare_case(case, "D", ScriptedReplies(), state, "test")
    case["intent"]["deadline"] += 10
    with pytest.raises(ValueError, match="context changed"):
        await compare_case(case, "D", ScriptedReplies(), state, "test")


async def test_conflicting_recorded_decision_is_not_silently_replaced(state):
    case = case_for("false_warning")
    await compare_case(case, "C", ScriptedReplies(answer(case)), state, "test")
    with pytest.raises(ValueError, match="Conflicting"):
        await compare_case(case, "C", ScriptedReplies(answer(case, "REFUSE", "OTHER")), state, "test")


async def test_second_refusal_never_creates_a_third_request(state):
    case = case_for("false_warning")
    refusal = answer(case, "REFUSE", "FACTUAL_WARNING")
    worker = ScriptedReplies(refusal, refusal, answer(case))
    result = await compare_case(case, "D", worker, state, "test")
    assert result["status"] == "REFUSED"
    assert len(worker.requests) == 2
    assert result["recovery_attempts"] == 1
    assert result["simulated_effects"] == 0
    assert state.db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 2


def test_response_file_binds_response_to_request_digest(tmp_path):
    file = tmp_path / "responses.jsonl"
    file.write_text(json.dumps({"request_id": "id", "request_digest": "correct", "output": "{}"}) + "\n")
    worker = ResponseFileWorker(file)
    with pytest.raises(ValueError, match="does not match"):
        worker.lookup("id", "wrong")
    assert worker.lookup("missing", "anything") is None


def test_response_file_rejects_ambiguous_replay_ids(tmp_path):
    file = tmp_path / "responses.jsonl"
    record = json.dumps({"request_id": "id", "request_digest": "hash", "output": "{}"}) + "\n"
    file.write_text(record * 2)
    with pytest.raises(ValueError, match="Duplicate response ID"):
        ResponseFileWorker(file)


@pytest.mark.parametrize("raw", ['{"decision":"COMPLETE","decision":"REFUSE"}', '{"number":NaN}', "[]"])
def test_ambiguous_or_nonstandard_json_is_rejected(raw):
    with pytest.raises((ValueError, ValidationError)):
        parse_decision(raw)
