"""Real upstream verification/discovery, simulated contract I/O only."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from eth_account import Account
from eth_account.messages import encode_defunct

from bnbagent.erc8183.job_ops import ERC8183JobOps
from bnbagent.erc8183.negotiation import NegotiationHandler, build_job_description
from bnbagent.erc8183.types import Job, JobStatus
from bnbagent.networks import AssetId, get_asset

COMMERCE = "0x" + "11" * 20
ROUTER = "0x" + "22" * 20
POLICY = "0x" + "44" * 20
CLIENT = "0x" + "33" * 20


def make_sdk_fixture(case):
    # Ephemeral local quote signer only. Never persisted, funded, or attached to ops.
    account = Account.create()
    signer = SimpleNamespace(
        address=account.address,
        sign_message=lambda message: {
            "signature": account.sign_message(encode_defunct(text=message)).signature
        },
    )
    token = get_asset(97, AssetId.TEST_U).address
    handler = NegotiationHandler(service_price="1000", currency=token,
                                 wallet_provider=signer, chain_id=97, verifying_contract=COMMERCE)
    with patch("bnbagent.erc8183.negotiation.time.time", return_value=case["now"] - 60):
        quote = handler.negotiate({
            "task_description": f"Analyze public state: {case['claim']}",
            "terms": {"deliverables": "structured analysis", "quality_standards": "factual"},
        })
    job = Job(id=1, client=CLIENT, provider=account.address, evaluator=ROUTER,
              description=build_job_description(quote.to_dict()), budget=1000,
              expired_at=case["now"] + 3600, status=JobStatus.FUNDED, hook=ROUTER)
    ops = ERC8183JobOps(provider_address=account.address, service_price=1000)
    client = MagicMock(name="simulated_contract_client")
    client.network.chain_id = client.w3.eth.chain_id = 97
    client.commerce.address = COMMERCE
    client.router.address = ROUTER
    client.router.job_policy.return_value = POLICY
    client.router.policy_whitelist.return_value = True
    client.policy.dispute_window.return_value = 60
    client.payment_token = token
    client.job_payment_token.return_value = token
    client.get_job_funded_block.return_value = 123
    client.w3.eth.get_block.return_value = {"timestamp": case["now"] - 30}
    client.w3.eth.get_code.return_value = b""
    client.get_job.return_value = job
    client.commerce.job_counter.return_value = 1
    client.commerce.get_jobs_batch.return_value = [job]
    ops._client = client  # Test-only injection; no SDK verification method is replaced.
    return ops, client
