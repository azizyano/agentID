import copy
import json
from dataclasses import replace

import pytest

from veriabstain_eval.dataset import build_manifest, canonical, load_manifest
from veriabstain_eval.runner import assess_reference, offline, run_case
from veriabstain_eval.sdk_fixture import make_sdk_fixture

MANIFEST, _ = load_manifest()


def test_frozen_manifest_matches_preregistered_design():
    assert MANIFEST == build_manifest()
    assert len({c["operation_id"] for c in MANIFEST["cases"]}) == 40
    assert len({c["condition"] for c in MANIFEST["cases"]}) == 10


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda c: c["id"])
async def test_all_frozen_scenarios_through_real_sdk(case):
    result = await run_case(case)
    assert result["passed"], result
    assert result["authorization_unchanged"]
    assert result["unauthorized_effects"] == result["duplicate_effects"] == 0
    assert result["callbacks"]  # Genuine SDK verification accepted the signed fixture.


@pytest.mark.parametrize("change", ["unsigned", "wrong_provider", "underfunded", "wrong_router", "expired"])
async def test_upstream_rejections_never_start_work(change):
    case = MANIFEST["cases"][0]
    ops, client = make_sdk_fixture(case)
    job = client.get_job.return_value
    if change == "unsigned":
        envelope = json.loads(job.description)
        envelope.pop("provider_sig")
        job = replace(job, description=json.dumps(envelope))
    elif change == "wrong_provider":
        job = replace(job, provider="0x" + "99" * 20)
    elif change == "underfunded":
        job = replace(job, budget=1)
    elif change == "wrong_router":
        job = replace(job, evaluator="0x" + "99" * 20)
    else:
        job = replace(job, expired_at=case["now"] - 1)
    client.get_job.return_value = job
    client.commerce.get_jobs_batch.return_value = [job]
    result = await run_case(case, ops=ops)
    assert result["callbacks"] == result["effects"] == []
    client.submit.assert_not_called()


async def test_keyless_fixture_cannot_submit_real_transaction():
    ops, client = make_sdk_fixture(MANIFEST["cases"][0])
    with pytest.raises(ValueError, match="signing wallet_provider"):
        await ops.submit_result(1, "must never leave this process")
    client.submit.assert_not_called()


@pytest.mark.parametrize("mutation", ["target", "arguments", "block_hash", "future_time", "not_finalized", "boolean_amount"])
def test_additional_evidence_mutations_fail_closed(mutation):
    case = copy.deepcopy(MANIFEST["cases"][0])
    read = case["read"]
    if mutation == "target":
        read["target"] = "0x" + "99" * 20
    elif mutation == "arguments":
        read["arguments"]["spender"] = "0x" + "99" * 20
    elif mutation == "block_hash":
        read["block_hash"] = "0x" + "zz" * 32
    elif mutation == "future_time":
        read["observed_at"] = case["now"] + 1
    elif mutation == "not_finalized":
        read["finalized"] = False
    else:
        read["value"] = True
    assert assess_reference(case["claim"], read, case["now"]) not in ("SUPPORTED", "CONTRADICTED")


async def test_case_labels_and_expected_results_are_not_worker_inputs():
    case = copy.deepcopy(MANIFEST["cases"][0])
    reference = await run_case(case)
    case["condition"] = "genuine_warning"
    case["expected"] = {"verdict": "SUPPORTED", "decision": "WRONG", "new_effects": 99}
    altered = await run_case(case)
    assert reference["actual"] == altered["actual"]
    assert not altered["passed"]


async def test_reference_run_is_repeatable_without_persisting_signer():
    case = MANIFEST["cases"][0]
    assert canonical(await run_case(case)) == canonical(await run_case(case))


@pytest.mark.parametrize("restriction", ["expired", "target", "chain", "actions"])
async def test_contradiction_never_overrides_original_restriction(restriction):
    case = copy.deepcopy(MANIFEST["cases"][0])
    if restriction == "expired":
        case["intent"]["deadline"] = case["now"]
    elif restriction == "target":
        case["intent"]["target"] = "0x" + "99" * 20
    elif restriction == "chain":
        case["intent"]["chain_id"] = 56
    else:
        case["intent"]["allowed_actions"] = []
    result = await run_case(case)
    assert result["actual"]["verdict"] == "CONTRADICTED"
    assert result["actual"]["decision"] == "ESCALATE"
    assert result["effects"] == []


def test_network_guard_blocks_accidental_connection():
    import socket
    with offline(), socket.socket() as connection:
        with pytest.raises(RuntimeError, match="Fixture network disabled"):
            connection.connect(("127.0.0.1", 8545))
