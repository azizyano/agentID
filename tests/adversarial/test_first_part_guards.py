"""Independent regressions for malformed evidence and untrusted replay data.

These tests exercise deterministic guards, not model behavior or real-chain safety.
"""

import copy
import json

import pytest

from veriabstain_eval.dataset import load_manifest
from veriabstain_eval.runner import assess_reference, policy_allows
from veriabstain_eval.workers import ResponseFileWorker, parse_decision


def fixture_case(predicate="erc20.allowance", condition="false_warning"):
    manifest, _ = load_manifest()
    return copy.deepcopy(next(case for case in manifest["cases"]
                              if case["claim"]["predicate"] == predicate
                              and case["condition"] == condition))


def test_partial_hash_hidden_by_whitespace_is_not_a_block_commitment():
    case = fixture_case()
    # Same textual length as bytes32, but fromhex silently ignores spaces.
    case["read"]["block_hash"] = "0x" + "ab" * 31 + "  "
    assert assess_reference(case["claim"], case["read"], case["now"]) == "INCONCLUSIVE"


def test_float_chain_id_does_not_match_integer_domain():
    case = fixture_case()
    case["read"]["chain_id"] = 97.0
    assert assess_reference(case["claim"], case["read"], case["now"]) == "INCONCLUSIVE"


def test_boolean_job_id_does_not_match_integer_argument():
    case = fixture_case("erc8183.job_status")
    assert case["claim"]["arguments"]["job_id"] == 1
    case["read"]["arguments"]["job_id"] = True
    assert assess_reference(case["claim"], case["read"], case["now"]) == "INCONCLUSIVE"


def test_boolean_secondary_value_cannot_confirm_zero_allowance():
    case = fixture_case(condition="genuine_warning")
    assert case["read"]["value"] == 0
    case["read"]["secondary_value"] = False
    assert assess_reference(case["claim"], case["read"], case["now"]) == "INCONCLUSIVE"


@pytest.mark.parametrize("source", [None, "", "   ", 123])
def test_missing_or_invalid_evidence_provenance_is_inconclusive(source):
    case = fixture_case()
    case["read"]["source"] = source
    assert assess_reference(case["claim"], case["read"], case["now"]) == "INCONCLUSIVE"


@pytest.mark.parametrize("mutation", ["missing_claim_chain", "malformed_target", "unsupported_arguments"])
def test_matching_malformed_context_is_not_supported(mutation):
    case = fixture_case()
    if mutation == "missing_claim_chain":
        case["claim"].pop("chain_id")
    elif mutation == "malformed_target":
        case["claim"]["target"] = case["read"]["target"] = "not-an-address"
    else:
        case["claim"]["arguments"] = {"unsupported": "argument"}
        case["read"]["arguments"] = {"unsupported": "argument"}
    assert assess_reference(case["claim"], case["read"], case["now"]) == "INCONCLUSIVE"


@pytest.mark.parametrize("field,value", [
    ("max_asset_spend", False), ("max_asset_spend", 0.0),
    ("chain_id", 97.0), ("deadline", 9_999_999_999.0),
])
def test_policy_rejects_coercible_noncanonical_authorization(field, value):
    case = fixture_case()
    case["intent"][field] = value
    assert policy_allows(case["intent"], case["claim"], case["now"]) is False


def test_missing_policy_field_is_denied_without_crashing():
    case = fixture_case()
    case["intent"].pop("allowed_actions")
    assert policy_allows(case["intent"], case["claim"], case["now"]) is False


def test_nested_worker_json_becomes_invalid_output_instead_of_recursion_failure():
    raw = "[" * 1_500 + "0" + "]" * 1_500
    assert len(raw.encode()) < 16_384
    with pytest.raises(ValueError):
        parse_decision(raw)


@pytest.mark.parametrize("record", [123, None, ["request_id", "request_digest", "output"]])
def test_nonobject_replay_record_is_cleanly_rejected(tmp_path, record):
    source = tmp_path / "responses.jsonl"
    source.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ResponseFileWorker(source)
