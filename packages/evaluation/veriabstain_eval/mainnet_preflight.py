"""Read-only BSC mainnet preflight for the exact MVP deployment package."""
import hashlib
import json
from pathlib import Path

from web3 import Web3

CHAIN_ID = 56
OFFICIAL_AGENT_ID_REGISTRY = Web3.to_checksum_address(
    '0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F'
)
REGISTRY_ABI = [
    {'type': 'function', 'name': 'name', 'stateMutability': 'view', 'inputs': [],
     'outputs': [{'name': '', 'type': 'string'}]},
    {'type': 'function', 'name': 'symbol', 'stateMutability': 'view', 'inputs': [],
     'outputs': [{'name': '', 'type': 'string'}]},
    {'type': 'function', 'name': 'balanceOf', 'stateMutability': 'view',
     'inputs': [{'name': 'owner', 'type': 'address'}],
     'outputs': [{'name': '', 'type': 'uint256'}]},
]


def load_deployment_package(directory):
    root = Path(directory)
    plan_bytes = (root / 'deployment-plan.json').read_bytes()
    manifest = json.loads((root / 'verification-manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256(plan_bytes).hexdigest() != manifest.get('deployment_plan_sha256'):
        raise ValueError('Deployment plan digest mismatch')
    plan = json.loads(plan_bytes)
    if (
        set(plan.get('constructor', {}).get('arguments', [])) != {OFFICIAL_AGENT_ID_REGISTRY}
        or plan.get('chain_id') != CHAIN_ID
        or plan.get('native_value_wei') != 0
        or plan.get('transactions_sent') != 0
        or plan.get('deployer') is not None
        or plan.get('signed_transaction') is not None
        or not isinstance(plan.get('deployment_data'), str)
        or not isinstance(plan.get('expected_runtime_keccak256'), str)
    ):
        raise ValueError('Unsupported deployment plan')
    return plan, manifest


def _read(function, block_number):
    return function.call(block_identifier=block_number)


def preflight_mainnet(w3, deployer, plan):
    if type(w3.eth.chain_id) is not int or w3.eth.chain_id != CHAIN_ID:
        raise ValueError('BSC mainnet chain 56 required')
    try:
        deployer = Web3.to_checksum_address(deployer)
    except (TypeError, ValueError) as error:
        raise ValueError('Invalid public deployer address') from error

    block = w3.eth.get_block('finalized')
    number = block['number']
    block_hash = Web3.to_hex(block['hash'])
    registry_code = w3.eth.get_code(OFFICIAL_AGENT_ID_REGISTRY, block_identifier=number)
    if not registry_code:
        raise ValueError('Official Agent ID registry has no finalized code')
    registry = w3.eth.contract(address=OFFICIAL_AGENT_ID_REGISTRY, abi=REGISTRY_ABI)
    name = _read(registry.functions.name(), number)
    symbol = _read(registry.functions.symbol(), number)
    holder_balance = _read(registry.functions.balanceOf(deployer), number)
    if name != 'SPACE ID Agent ID' or symbol != 'AI' or type(holder_balance) is not int:
        raise ValueError('Official Agent ID registry identity mismatch')

    deployment = {
        'from': deployer,
        'value': 0,
        'data': plan['deployment_data'],
    }
    simulated_runtime = w3.eth.call(deployment, block_identifier=number)
    simulated_runtime_hash = Web3.to_hex(Web3.keccak(simulated_runtime))
    if simulated_runtime_hash.lower() != plan['expected_runtime_keccak256'].lower():
        raise ValueError('Simulated deployment runtime mismatch')

    estimated_gas = w3.eth.estimate_gas(deployment, block_identifier=number)
    gas_price = w3.eth.gas_price
    deployer_balance = w3.eth.get_balance(deployer, block_identifier=number)
    if any(type(value) is not int or value < 0 for value in (estimated_gas, gas_price, deployer_balance)):
        raise ValueError('Invalid gas or balance response')
    gas_limit = (estimated_gas * 120 + 99) // 100
    maximum_cost = gas_limit * gas_price
    funded = deployer_balance >= maximum_cost
    if w3.eth.get_block(number)['hash'] != block['hash']:
        raise ValueError('Finalized block changed during preflight')

    return {
        'status': 'MAINNET_PREFLIGHT_READY' if funded else 'MAINNET_PREFLIGHT_NEEDS_BNB',
        'assurance': 'RPC_FINALIZED_READ',
        'chain_id': CHAIN_ID,
        'finalized_block_number': number,
        'finalized_block_hash': block_hash,
        'agent_id_registry': OFFICIAL_AGENT_ID_REGISTRY,
        'registry_code_keccak256': Web3.to_hex(Web3.keccak(registry_code)),
        'registry_name': name,
        'registry_symbol': symbol,
        'deployer': deployer,
        'deployer_holds_agent_id': holder_balance > 0,
        'deployer_agent_id_balance': holder_balance,
        'deployment_data_keccak256': Web3.to_hex(Web3.keccak(hexstr=plan['deployment_data'])),
        'simulated_runtime_keccak256': simulated_runtime_hash,
        'estimated_gas': estimated_gas,
        'proposed_gas_limit': gas_limit,
        'gas_price_wei': gas_price,
        'maximum_estimated_cost_wei': maximum_cost,
        'deployer_balance_wei': deployer_balance,
        'balance_sufficient': funded,
        'transactions_sent': 0,
        'limitations': 'Provider-trusted finalized reads and latest gas price; simulation is not deployment or BscScan verification',
    }
