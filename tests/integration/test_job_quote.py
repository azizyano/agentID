import copy
import json
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from bnbagent.erc8183.quote_verify import quote_content_error
from veriabstain_eval.job_quote import prepare_quote, import_signature, metamask_script

ROOT = Path(__file__).resolve().parents[2]
NOW = 1_795_200_000


def inputs():
    proposal = json.loads((ROOT / "config/job-proposal.json").read_text())
    draft = json.loads((ROOT / "config/testnet-job.draft.json").read_text())
    account = Account.create()
    proposal["provider"] = draft["provider"] = account.address
    return account, proposal, draft


def test_actual_personal_sign_encoding_recovers_provider_and_preserves_budget():
    account, proposal, draft = inputs()
    request = prepare_quote(proposal, draft, NOW)
    assert bytes.fromhex(request["wallet_request"]["params"][0][2:]).decode() == request["message_to_sign"]
    signature = Web3.to_hex(account.sign_message(encode_defunct(text=request["message_to_sign"])).signature)
    spec = import_signature(request, signature, proposal, draft, NOW + 10)
    assert spec["budget"] == 10**18 and spec["expired_at"] == NOW + 3600
    assert quote_content_error(spec["quote"]) is None
    assert request["transactions_sent"] == 0


@pytest.mark.parametrize("change", ["budget", "chain", "wallet", "deadline", "message", "expired", "wrong_signer", "raw_hash_bytes"])
def test_changed_or_wrong_signing_context_cannot_be_imported(change):
    account, proposal, draft = inputs()
    request = prepare_quote(proposal, draft, NOW)
    when = NOW + 10
    signing_account = Account.create() if change == "wrong_signer" else account
    message = encode_defunct(hexstr=request["message_to_sign"]) if change == "raw_hash_bytes" else encode_defunct(text=request["message_to_sign"])
    signature = Web3.to_hex(signing_account.sign_message(message).signature)
    if change == "budget":
        request["spec"]["budget"] = 2 * 10**18
    elif change == "chain":
        request["quote"]["chain_id"] = 56
    elif change == "wallet":
        request["spec"]["provider"] = Account.create().address
    elif change == "deadline":
        request["spec"]["expired_at"] += 3600
    elif change == "message":
        request["message_to_sign"] = "0x" + "00" * 32
    elif change == "expired":
        when = NOW + 900
    with pytest.raises(ValueError):
        import_signature(request, signature, proposal, draft, when)


def test_unapproved_job_cannot_create_a_signing_request():
    _, proposal, draft = inputs()
    proposal["status"] = "PROPOSED_FOR_OWNER_REVIEW"
    with pytest.raises(ValueError, match="Approved"):
        prepare_quote(proposal, draft, NOW)


def test_budget_cannot_expand_from_owner_approved_one_u():
    _, proposal, draft = inputs()
    proposal["proposed_budget_raw"] = str(2 * 10**18)
    with pytest.raises(ValueError, match="exactly 1"):
        prepare_quote(proposal, draft, NOW)


def test_browser_helper_only_requests_accounts_chain_and_personal_signature():
    _, proposal, draft = inputs()
    script = metamask_script(prepare_quote(proposal, draft, NOW))
    assert "personal_sign" in script and "eth_chainId" in script
    assert all(word not in script for word in ("eth_sendTransaction", "eth_signTypedData", "fetch(", "private_key", "approve("))
