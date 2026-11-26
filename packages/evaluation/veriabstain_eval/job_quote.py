"""Public offline signing request compatible with the pinned SDK's EIP-191 quote."""

import copy
import hashlib
import re
from unittest.mock import patch

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from bnbagent.erc8183.negotiation import NegotiationHandler, _build_description_content, build_job_description
from .dataset import canonical
from .testnet_plan import TestnetJobSpec


def prepare_quote(proposal, draft, now):
    proposal, draft = copy.deepcopy(proposal), copy.deepcopy(draft)
    if proposal.get("status") != "APPROVED_BY_OWNER" or type(now) is not int or now <= 0:
        raise ValueError("Approved job and exact timestamp required")
    if type(proposal.get("chain_id")) is not int or proposal["chain_id"] != 97 or type(draft.get("chain_id")) is not int or draft["chain_id"] != 97:
        raise ValueError("Only BSC testnet is supported")
    for name in ("client", "provider", "payment_token"):
        if proposal.get(name) != draft.get(name):
            raise ValueError("Approved wallet or token differs from draft")
    amount = proposal.get("proposed_budget_raw")
    if amount != "1000000000000000000" or proposal.get("proposed_budget_u") != "1":
        raise ValueError("This approval authorizes exactly 1 test U")
    lifetime = proposal.get("proposed_expiry_seconds_after_quote")
    fields = proposal.get("acceptance_fields")
    if type(lifetime) is not int or lifetime != 3600 or not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
        raise ValueError("Unsupported original job acceptance/deadline")
    spec = {**draft, "budget": int(amount), "expired_at": now + lifetime}
    handler = NegotiationHandler(service_price=amount, currency=spec["payment_token"],
                                 chain_id=97, verifying_contract=spec["commerce"],
                                 quote_ttl_seconds=900)
    task = (proposal["task"] + " Token=" + spec["payment_token"] + "; owner=" + spec["client"]
            + "; spender=" + spec["commerce"] + ". Analysis only; no worker asset actions.")
    with patch("bnbagent.erc8183.negotiation.time.time", return_value=now):
        quote = handler.negotiate({"task_description": task,
                                  "terms": {"deliverables": "JSON: " + ", ".join(fields),
                                            "quality_standards": "Exact read-only allowance at one finalized BSC testnet block; include its hash."}}).to_dict()
    quote.update(chain_id=97, verifying_contract=spec["commerce"])
    content = _build_description_content(quote, chain_id=97, verifying_contract=spec["commerce"])
    message = Web3.to_hex(Web3.keccak(text=canonical(content)))
    quote["negotiation_hash"] = message
    # This is an unsigned request, not a synthetic signature or wallet provider.
    TestnetJobSpec.model_validate({**spec, "quote": quote})
    return {"status": "AWAITING_PROVIDER_SIGNATURE", "created_at": now,
            "expires_at": now + 900, "job_expires_at": spec["expired_at"],
            "approved_proposal_sha256": hashlib.sha256(canonical(proposal).encode()).hexdigest(),
            "spec": spec, "quote": quote, "review_content": content,
            "message_to_sign": message,
            # The SDK signs the ASCII 0x-prefixed hash string, NOT raw hash bytes.
            "wallet_request": {"method": "personal_sign", "params": [Web3.to_hex(text=message), spec["provider"]]},
            "transactions_sent": 0}


def import_signature(request, signature, proposal, draft, now):
    expected = prepare_quote(proposal, draft, request.get("created_at"))
    if canonical(expected) != canonical(request):
        raise ValueError("Signing request changed from the approved job")
    if type(now) is not int or not request["created_at"] <= now < request["expires_at"]:
        raise ValueError("Signing request expired; do not reuse it")
    if not isinstance(signature, str) or not re.fullmatch(r"0x[0-9a-fA-F]{130}", signature):
        raise ValueError("Expected a public 65-byte MetaMask signature")
    signer = Account.recover_message(encode_defunct(text=request["message_to_sign"]), signature=signature)
    if signer.lower() != request["spec"]["provider"].lower():
        raise ValueError("Quote was not signed by the approved provider")
    spec = {**request["spec"], "quote": {**request["quote"], "provider_sig": signature}}
    validated = TestnetJobSpec.model_validate(spec)
    build_job_description(validated.quote)  # Preserve the upstream size/format gate.
    return validated.model_dump()


def metamask_script(request):
    # Literal public values only. No fetch, transaction request, approval, or key access.
    import json
    return """// Review request.json first. This requests a public job-quote signature only.
(async () => {
  const expected = EXPECTED;
  const expires = EXPIRES;
  const message = MESSAGE;
  const provider = window.ethereum;
  if (!provider) throw new Error('MetaMask provider not found');
  if (Date.now() / 1000 >= expires) throw new Error('Quote expired; stop and request a fresh unsigned quote');
  if (await provider.request({method: 'eth_chainId'}) !== '0x61') throw new Error('Select BSC testnet 97');
  const accounts = await provider.request({method: 'eth_requestAccounts'});
  if (!accounts[0] || accounts[0].toLowerCase() !== expected.toLowerCase())
    throw new Error('Select the provider wallet ending B3c1 in MetaMask');
  console.log('Provider quote: 1 test U; read-only allowance analysis; no asset action. Message:', message);
  const hex = '0x' + Array.from(new TextEncoder().encode(message), b => b.toString(16).padStart(2, '0')).join('');
  const signature = await provider.request({method: 'personal_sign', params: [hex, expected]});
  console.log('PUBLIC_PROVIDER_SIGNATURE', signature);
  return signature;
})();
""".replace("EXPECTED", json.dumps(request["spec"]["provider"])).replace("EXPIRES", str(request["expires_at"])).replace("MESSAGE", json.dumps(request["message_to_sign"]))
