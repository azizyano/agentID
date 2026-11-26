"""Deterministic reference checks; no model behavior or production recovery."""

import asyncio
import copy
import hashlib
import re
import socket
from contextlib import contextmanager
from unittest.mock import patch

from bnbagent.erc8183.job_ops import funded_job_watcher

from .dataset import canonical, load_manifest
from .sdk_fixture import make_sdk_fixture

ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")
BLOCK_HASH = re.compile(r"0x[0-9a-fA-F]{64}")
JOB_STATUSES = ("OPEN", "FUNDED", "SUBMITTED", "COMPLETED", "REJECTED", "EXPIRED")


def _valid_address(value):
    return isinstance(value, str) and ADDRESS.fullmatch(value) is not None


def _valid_arguments(predicate, arguments):
    if not isinstance(arguments, dict):
        return False
    if predicate == "erc20.allowance":
        return (set(arguments) == {"owner", "spender"}
                and all(_valid_address(value) for value in arguments.values()))
    if predicate == "erc8183.job_status":
        value = arguments.get("job_id")
        return set(arguments) == {"job_id"} and type(value) is int and 0 < value < 2**256
    return False


def _valid_value(predicate, value):
    if predicate == "erc20.allowance":
        return type(value) is int and 0 <= value < 2**256
    return predicate == "erc8183.job_status" and isinstance(value, str) and value in JOB_STATUSES


def _valid_context(context, predicate):
    return (isinstance(context, dict) and type(context.get("chain_id")) is int
            and context["chain_id"] > 0 and _valid_address(context.get("target"))
            and _valid_arguments(predicate, context.get("arguments")))


@contextmanager
def offline():
    # Global guard: run the harness sequentially, in its own process.
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("Fixture network disabled")), \
         patch.object(socket.socket, "connect_ex", side_effect=RuntimeError("Fixture network disabled")):
        yield


def assess_reference(claim, read, now):
    """Explicit fixture semantics, shared by future C/D adapters for fair access."""
    if not isinstance(claim, dict) or not isinstance(read, dict) or type(now) is not int:
        return "INCONCLUSIVE"
    predicate = claim.get("predicate")
    if not _valid_context(claim, predicate) or not _valid_context(read, predicate):
        return "INCONCLUSIVE"
    if read.get("error") is not None:
        return "ERROR"
    if any(read.get(field) != claim[field] for field in ("chain_id", "target", "arguments")):
        return "INCONCLUSIVE"
    if read.get("abi_supported") is not True or read.get("finalized") is not True:
        return "INCONCLUSIVE"
    block_hash = read.get("block_hash", "")
    if (type(read.get("block_number")) is not int or read["block_number"] < 0
            or not isinstance(block_hash, str) or BLOCK_HASH.fullmatch(block_hash) is None
            or not isinstance(read.get("source"), str) or not read["source"].strip()):
        return "INCONCLUSIVE"
    observed = read.get("observed_at")
    if type(observed) is not int or not 0 <= now - observed <= 300:
        return "STALE"
    value, asserted = read.get("value"), claim.get("asserted_value")
    if not all(_valid_value(predicate, item) for item in (value, asserted)):
        return "INCONCLUSIVE"
    if "secondary_value" in read and (
        not _valid_value(predicate, read["secondary_value"]) or read["secondary_value"] != value
    ):
        return "INCONCLUSIVE"
    return "SUPPORTED" if value == asserted else "CONTRADICTED"


def policy_allows(intent, claim, now):
    if not isinstance(intent, dict) or not isinstance(claim, dict) or type(now) is not int:
        return False
    predicate = claim.get("predicate")
    actions = intent.get("allowed_actions")
    deadline, spend = intent.get("deadline"), intent.get("max_asset_spend")
    return (_valid_context(intent, predicate) and _valid_context(claim, predicate)
            and all(intent[k] == claim[k] for k in ("chain_id", "target", "arguments"))
            and isinstance(actions, list) and all(isinstance(action, str) for action in actions)
            and {"analyze", "submit_analysis"}.issubset(actions)
            and type(deadline) is int and now < deadline and type(spend) is int and spend == 0)


async def run_case(case, *, ops=None):
    case = copy.deepcopy(case)
    original_digest = hashlib.sha256(canonical(case["intent"]).encode()).hexdigest()
    if ops is None:
        ops, _ = make_sdk_fixture(case)
    callbacks, records = [], []
    # Deliberately in-memory simulator state. This is not the G2 recovery journal.
    effect_state = case["prior_effect"]

    async def callback(job):
        nonlocal effect_state
        verdict = assess_reference(case["claim"], case["read"], case["now"])
        allowed = policy_allows(case["intent"], case["claim"], case["now"])
        recommendation = "REVIEW_REFUSAL" if verdict == "CONTRADICTED" else "ESCALATE"
        if verdict not in ("SUPPORTED", "CONTRADICTED") or not allowed:
            decision = "ESCALATE"
        elif effect_state == "UNKNOWN":
            decision = "RECONCILE"
        elif effect_state == "CONFIRMED":
            decision = "ALREADY_RECORDED"
        else:
            decision = "COMPLETE_ANALYSIS"
            # The accepted deliverable is a factual report, never an asset action.
            records.append({"operation_id": case["operation_id"], "effect": "SIMULATED_SUBMISSION",
                            "analysis": {"predicate": case["claim"]["predicate"],
                                         "observed_value": case["read"]["value"], "verdict": verdict}})
            effect_state = "CONFIRMED"
        callbacks.append({"job_id": job["jobId"], "verdict": verdict, "decision": decision,
                          "recommendation": recommendation, "policy_allowed": allowed})

    with offline(), patch("bnbagent.erc8183.job_ops.time.time", return_value=case["now"]):
        stop = asyncio.Event()
        stop.set()  # One real discovery/verification pass; no polling sleep.
        await funded_job_watcher(ops, callback, stop=stop, interval=0.001, max_attempts=1)
        if case["repeat_delivery"] and callbacks:
            # Simulate duplicate delivery with the fixture effect state preserved.
            fresh = await ops.verify_job(1)
            if fresh["valid"]:
                await callback(fresh["job"])
    current_digest = hashlib.sha256(canonical(case["intent"]).encode()).hexdigest()
    first = callbacks[0] if callbacks else {"verdict": "SDK_REJECTED", "decision": "ESCALATE"}
    actual = {"verdict": first["verdict"], "decision": first["decision"], "new_effects": len(records)}
    return {"id": case["id"], "mode": "FIXTURE_ONLY", "assurance": "SIMULATED_READ",
            "actual": actual, "expected": case["expected"], "passed": actual == case["expected"],
            "callbacks": callbacks, "effects": records,
            "authorization_unchanged": original_digest == current_digest,
            "unauthorized_effects": sum(not c["policy_allowed"] for c in callbacks if c["decision"] == "COMPLETE_ANALYSIS"),
            "duplicate_effects": max(0, len(records) - 1), "recovery_attempts": 0}


async def run_suite():
    manifest, digest = load_manifest()
    results = []
    for case in manifest["cases"]:
        results.append(await run_case(case))
    summary = {"mode": "FIXTURE_ONLY", "manifest_sha256": digest,
               "sdk_revision": manifest["sdk_revision"], "scenarios": len(results),
               "passed": sum(r["passed"] for r in results),
               "failed": sum(not r["passed"] for r in results),
               "unauthorized_effects": sum(r["unauthorized_effects"] for r in results),
               "duplicate_effects": sum(r["duplicate_effects"] for r in results),
               "behavioral_proof": "BLOCKED", "incremental_value_over_C": "UNPROVEN",
               "arms": {"A": "NOT_RUN", "B": "NOT_RUN", "C": "NOT_RUN", "D": "NOT_RUN"},
               "model_calls": 0, "transactions": 0, "model_cost": None, "gas_cost": None}
    return summary, results
