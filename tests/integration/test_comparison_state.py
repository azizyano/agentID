"""Integrity and concurrent-resumption checks for the experiment ledger."""

import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from veriabstain_eval.comparison_state import ComparisonState
from veriabstain_eval.workers import digest


def envelope(label="first", request_id=None):
    body = {"messages": [{"role": "user", "content": label}]}
    return {"request_id": request_id or digest(label),
            "request_digest": digest(body), "request": body}


@pytest.fixture
def state(tmp_path):
    instance = ComparisonState(tmp_path / "state.sqlite3")
    yield instance
    instance.close()


def test_body_must_match_its_digest_before_reservation(state):
    request = envelope()
    request["request"]["messages"][0]["content"] = "changed"
    with pytest.raises(ValueError, match="digest"):
        state.prepare("operation", {"intent": "original"}, 0, request)
    assert state.db.execute("SELECT COUNT(*) FROM scopes").fetchone()[0] == 0


def test_global_request_collision_cannot_replay_another_operations_response(state):
    request = envelope()
    state.prepare("first-operation", {"intent": "first"}, 0, request)
    state.record(request, "first response")
    with pytest.raises(ValueError, match="bound|operation"):
        state.prepare("second-operation", {"intent": "second"}, 0, request)
    assert state.db.execute("SELECT COUNT(*) FROM scopes").fetchone()[0] == 1


def test_cached_response_cannot_hide_a_different_request_digest(state):
    original = envelope()
    state.prepare("operation", {}, 0, original)
    state.record(original, "response")
    changed = envelope("different body", request_id=original["request_id"])
    with pytest.raises(ValueError, match="request|digest"):
        state.record(changed, "response")


@pytest.mark.parametrize("mutation", ["response", "response_digest", "payload", "partial_response"])
def test_stored_record_corruption_fails_closed(state, mutation):
    request = envelope()
    state.prepare("operation", {}, 0, request)
    state.record(request, "saved response")
    updates = {
        "response": ("response", "changed response"),
        "response_digest": ("response_digest", "bad hash"),
        "payload": ("payload", "{}"),
        "partial_response": ("response_digest", None),
    }
    column, value = updates[mutation]
    # Column names come exclusively from the fixed test table above.
    state.db.execute(f"UPDATE requests SET {column}=?", (value,))
    state.db.commit()
    with pytest.raises(ValueError, match="stored|corrupt|integrity|digest|envelope"):
        state.prepare("operation", {}, 0, request)


def test_retry_requires_an_observed_first_response(state):
    state.prepare("operation", {}, 0, envelope())
    with pytest.raises(ValueError, match="observed first"):
        state.prepare("operation", {}, 1, envelope("retry"))
    assert state.db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 1


@pytest.mark.parametrize("round_number", [True, False, -1, 2, 0.0, "0"])
def test_round_slot_is_a_strict_bounded_integer(state, round_number):
    with pytest.raises(ValueError, match="round"):
        state.prepare("operation", {}, round_number, envelope())


def test_closed_and_reopened_ledger_returns_only_bound_response(tmp_path):
    path = tmp_path / "state.sqlite3"
    request = envelope()
    first = ComparisonState(path)
    first.prepare("operation", {}, 0, request)
    first.record(request, "saved")
    first.close()
    resumed = ComparisonState(path)
    try:
        assert resumed.prepare("operation", {}, 0, request) == "saved"
        resumed.record(copy.deepcopy(request), "saved")
        assert resumed.db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 1
    finally:
        resumed.close()


def test_concurrent_global_id_collision_reserves_only_one_operation(tmp_path):
    path = tmp_path / "state.sqlite3"
    initial = ComparisonState(path)
    initial.close()
    barrier = Barrier(2)
    request = envelope()

    def reserve(operation):
        connection = ComparisonState(path)
        try:
            barrier.wait(timeout=5)
            try:
                connection.prepare(operation, {"intent": operation}, 0, request)
                return "reserved"
            except ValueError:
                return "rejected"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, ("first", "second")))
    assert sorted(outcomes) == ["rejected", "reserved"]
    final = ComparisonState(path)
    try:
        assert final.db.execute("SELECT COUNT(*) FROM scopes").fetchone()[0] == 1
        assert final.db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 1
    finally:
        final.close()


def test_concurrent_conflicting_responses_cannot_replace_the_winner(tmp_path):
    path = tmp_path / "state.sqlite3"
    request = envelope()
    initial = ComparisonState(path)
    initial.prepare("operation", {}, 0, request)
    initial.close()
    barrier = Barrier(2)

    def record(response):
        connection = ComparisonState(path)
        try:
            barrier.wait(timeout=5)
            try:
                connection.record(request, response)
                return "recorded"
            except ValueError:
                return "rejected"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(record, ("first", "second")))
    assert sorted(outcomes) == ["recorded", "rejected"]
    final = ComparisonState(path)
    try:
        assert final.prepare("operation", {}, 0, request) in ("first", "second")
    finally:
        final.close()
