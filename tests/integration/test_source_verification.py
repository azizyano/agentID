"""Unit checks on bytecode comparison, not claims of live source equivalence."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("source_verification", Path(__file__).resolve().parents[2] / "tools/verify_testnet_sources.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_metadata_removal_keeps_executable_difference_visible():
    assert module.without_metadata(b"\x60\x01\xa0\x00\x01") == b"\x60\x01"
    assert module.without_metadata(b"\x60\x02\xa0\x00\x01") != b"\x60\x01"


@pytest.mark.parametrize("raw", [b"", b"\x60\x01", b"\x60\x01\xff\x00\x01", b"\xa0\xff\xff"])
def test_invalid_metadata_trailer_is_not_silently_ignored(raw):
    with pytest.raises(ValueError):
        module.without_metadata(raw)


def test_unknown_immutable_cannot_be_masked_as_a_match():
    compiled = {"contract": {"evm": {"deployedBytecode": {"object": "00" * 32,
                 "immutableReferences": {"1": [{"start": 0, "length": 32}]}, "linkReferences": {}}}},
                "immutable_names": {"1": "unreviewed_field"}}
    with pytest.raises(ValueError, match="Unreviewed immutable"):
        module.linked_runtime(compiled, "0x" + "11" * 20)


def test_abi_shape_detects_output_and_mutability_changes():
    entry = {"type": "function", "name": "get", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "view"}
    changed = {**entry, "outputs": [{"type": "address"}]}
    assert module.function_shapes([entry]) != module.function_shapes([changed])
    assert module.function_shapes([entry]) != module.function_shapes([{**entry, "stateMutability": "nonpayable"}])
