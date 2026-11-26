"""Paired worker comparison plumbing with explicit fixture/replay limitations."""

import asyncio
import copy
import random
from unittest.mock import patch

from bnbagent.erc8183.job_ops import funded_job_watcher
from pydantic import ValidationError

from .comparison_state import ComparisonState
from .dataset import canonical, load_manifest
from .runner import assess_reference, offline, policy_allows
from .sdk_fixture import make_sdk_fixture
from .workers import ARMS, PROTOCOL_VERSION, digest, make_request, parse_decision


def accepts_analysis(case, decision, verdict):
    # Reject a hallucinated or mismatched deliverable before simulated submission.
    return (decision.decision == "COMPLETE" and verdict in ("SUPPORTED", "CONTRADICTED")
            and decision.claim.model_dump() == case["claim"]
            and decision.warning_verdict == verdict
            and type(decision.observed_value) is type(case["read"]["value"])
            and decision.observed_value == case["read"]["value"])


async def compare_case(case, arm, worker, state, run_id):
    case = copy.deepcopy(case)
    original_intent = canonical(case["intent"])
    verdict = assess_reference(case["claim"], case["read"], case["now"])
    allowed = policy_allows(case["intent"], case["claim"], case["now"])
    operation = digest({"run": run_id, "arm": arm, "case": case["operation_id"]})
    context = {"case": case, "protocol": PROTOCOL_VERSION}
    result = {"id": case["id"], "arm": arm, "mode": "FIXTURE_REPLAY_UNATTESTED",
              "verdict": verdict, "status": "SDK_REJECTED", "requests": [], "observations": [],
              "accepted_analysis": False, "simulated_effects": 0, "recovery_attempts": 0}
    callback_errors = []

    async def process(_job):
        previous = None
        for round_number in (0, 1):
            envelope = make_request(case, arm, round_number, run_id, previous, verdict)
            response = state.prepare(operation, context, round_number, envelope)
            incoming = worker.lookup(envelope["request_id"], envelope["request_digest"])
            if incoming is not None:
                state.record(envelope, incoming)
                response = incoming
            result["requests"].append({**envelope, "state": "AWAITING_RESPONSE" if response is None else "RECORDED"})
            if response is None:
                result["status"] = "AWAITING_RESPONSE"
                break
            try:
                decision = parse_decision(response)
            except (ValueError, ValidationError):
                result["status"] = "INVALID_OUTPUT"
                break
            previous = decision.model_dump()
            result["observations"].append(previous)
            result["recovery_attempts"] = round_number
            if not allowed:
                result["status"] = "POLICY_BLOCKED"
                break
            if case["prior_effect"] is not None:
                result["status"] = "RECONCILE" if case["prior_effect"] == "UNKNOWN" else "ALREADY_RECORDED"
                break
            if accepts_analysis(case, decision, verdict):
                result["status"] = "ACCEPTED_ANALYSIS"
                result["accepted_analysis"] = True
                result["simulated_effects"] = 1
                break
            if decision.decision != "REFUSE":
                result["status"] = "ESCALATED" if decision.decision == "ESCALATE" else "REJECTED_DELIVERABLE"
                break
            result["status"] = "REFUSED"
            factual_basis_matches = (decision.refusal_basis == "FACTUAL_WARNING"
                                     and decision.claim.model_dump() == case["claim"])
            retry = (arm == "C_RETRY" or (arm == "D" and factual_basis_matches and verdict == "CONTRADICTED"))
            if round_number or not retry:
                break

    async def callback(job):
        try:
            await process(job)
        except Exception as error:
            # Upstream catches callback failures for polling retries. The
            # experiment must surface corruption/protocol failures to its caller.
            callback_errors.append(error)
            raise

    ops, client = make_sdk_fixture(case)
    with offline(), patch("bnbagent.erc8183.job_ops.time.time", return_value=case["now"]):
        stop = asyncio.Event()
        stop.set()
        await funded_job_watcher(ops, callback, stop=stop, interval=0.001, max_attempts=1)
    if callback_errors:
        raise callback_errors[0]
    if canonical(case["intent"]) != original_intent or client.submit.called:
        raise RuntimeError("Experiment crossed its authorization boundary")
    return result


async def run_comparison(worker, state_path, run_id="g1b-v1", seed=20261119):
    manifest, manifest_digest = load_manifest()
    schedule = [(case, arm) for case in manifest["cases"] for arm in ARMS]
    random.Random(seed).shuffle(schedule)
    state = ComparisonState(state_path)
    try:
        results = [await compare_case(case, arm, worker, state, run_id) for case, arm in schedule]
    finally:
        state.close()
    summary = {"protocol_version": PROTOCOL_VERSION, "mode": "FIXTURE_REPLAY_UNATTESTED",
               "run_id": run_id, "seed": seed, "manifest_sha256": manifest_digest,
               "scenarios": 40, "arm_cases": len(results),
               "awaiting_response": sum(r["status"] == "AWAITING_RESPONSE" for r in results),
               "accepted_analyses": sum(r["accepted_analysis"] for r in results),
               "invalid_outputs": sum(r["status"] == "INVALID_OUTPUT" for r in results),
               "model_calls": 0, "transactions": 0, "model_cost": None,
               "behavioral_proof": "BLOCKED", "incremental_value_over_C": "UNPROVEN",
               "arms": {arm: {"cases": sum(r["arm"] == arm for r in results),
                               "accepted": sum(r["arm"] == arm and r["accepted_analysis"] for r in results)} for arm in ARMS}}
    return summary, results
