"""Independent RPC-provider-trusted reads for the reviewed BSC testnet deployment."""
from web3 import Web3
from bnbagent.core.abis import load_abi

from .deliverables import Scope, Evidence
from .testnet_deployment import PINNED, REVIEWED_COMMERCE_CODE_HASH

TOKEN = '0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565'
TOKEN_HASH = '0xae12b1d61f7ed4febf649ccf319cb49a0e921cca3739dcb01b47d316049d46ff'
COMMERCE = '0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE'
PROXY_HASH = '0x1f1858db4825be798342d4c094630bf5ddc685bd802a083d8d88f15a6cdb2a89'
IMPLEMENTATION_SLOT = int.from_bytes(Web3.keccak(text='eip1967.proxy.implementation'), 'big') - 1
JOB_STATUSES = ('OPEN', 'FUNDED', 'SUBMITTED', 'COMPLETED', 'REJECTED', 'EXPIRED')


def collect_evidence(w3, scope, *, now, pinned_block_number=None):
    """No signer, credentials, worker output, transaction or caller-selected ABI.

    Network/code restrictions are deliberately narrow. Supporting another token,
    chain, or deployment requires separate source/ABI review and a new pin.
    """
    scope = Scope.model_validate(scope)
    if type(now) is not int or now < 0 or scope.chain_id != 97:
        raise ValueError('Only reviewed BSC testnet97 is supported')
    chain = w3.eth.chain_id
    if type(chain) is not int or chain != 97:
        raise ValueError('RPC chain differs from approved chain')
    expected = TOKEN if scope.predicate == 'erc20.allowance' else COMMERCE
    if scope.target.lower() != expected.lower():
        raise ValueError('Target lacks reviewed ABI/runtime pin')
    finalized = w3.eth.get_block('finalized')
    if pinned_block_number is not None:
        if (type(pinned_block_number) is not int or pinned_block_number < 0
                or type(finalized['number']) is not int or pinned_block_number > finalized['number']):
            raise ValueError('Requested block is not finalized')
        block = w3.eth.get_block(pinned_block_number)
        if block['number'] != pinned_block_number:
            raise ValueError('RPC returned another block')
    else:
        block = finalized
    number, timestamp = block['number'], block['timestamp']
    if (type(number) is not int or number < 0 or type(timestamp) is not int
            or not 0 <= now - timestamp <= 120 or len(block['hash']) != 32):
        raise ValueError('Missing, stale or future finalized block')
    block_hash = Web3.to_hex(block['hash'])
    target = Web3.to_checksum_address(scope.target)
    code_hash = Web3.to_hex(Web3.keccak(w3.eth.get_code(target, block_identifier=number)))
    expected_hash = TOKEN_HASH if scope.predicate == 'erc20.allowance' else PROXY_HASH
    if code_hash != expected_hash:
        raise ValueError('Reviewed target runtime changed')
    if scope.predicate == 'erc8183.job_status':
        storage = w3.eth.get_storage_at(target, IMPLEMENTATION_SLOT, block_identifier=number)
        if len(storage) != 32 or storage[:12] != bytes(12):
            raise ValueError('Invalid implementation slot')
        implementation = Web3.to_checksum_address(storage[-20:])
        if (implementation != PINNED.commerce_impl or
                Web3.to_hex(Web3.keccak(w3.eth.get_code(implementation, block_identifier=number)))
                != REVIEWED_COMMERCE_CODE_HASH):
            raise ValueError('Reviewed commerce implementation changed')
        contract = w3.eth.contract(address=target, abi=load_abi('AgenticCommerce.json'))
        raw = contract.functions.getJob(scope.arguments['job_id']).call(block_identifier=number)
        if (len(raw) != 11 or type(raw[0]) is not int or raw[0] != scope.arguments['job_id']
                or type(raw[7]) is not int or not 0 <= raw[7] < len(JOB_STATUSES)):
            raise ValueError('Missing job or unsupported job response')
        value = JOB_STATUSES[raw[7]]
    else:
        contract = w3.eth.contract(address=target, abi=load_abi('ERC20.json'))
        value = contract.functions.allowance(
            Web3.to_checksum_address(scope.arguments['owner']),
            Web3.to_checksum_address(scope.arguments['spender'])).call(block_identifier=number)
    if Web3.to_hex(w3.eth.get_block(number)['hash']) != block_hash or w3.eth.chain_id != 97:
        raise ValueError('Pinned snapshot or chain changed')
    result = {**scope.model_dump(), 'schema_version': 1, 'block_number': number,
              'block_hash': block_hash, 'value': value, 'source': 'bsc-testnet-public-rpc-v1',
              'assurance': 'RPC_FINALIZED_READ', 'observed_at': now, 'finalized': True,
              'canonical': True, 'abi_supported': True, 'error': None, 'conflicting': False}
    return Evidence.model_validate(result).model_dump()
