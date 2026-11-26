"""Finalized read-only reconciliation of the MVP BSC mainnet deployment."""
import re

from web3 import Web3

CHAIN_ID = 56
EXPECTED_DEPLOYER = Web3.to_checksum_address('0xb16b77C16773DEF8fA279A1228Eba9308eCD7841')
OFFICIAL_REGISTRY = Web3.to_checksum_address('0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F')


def _read(contract, name, block_number):
    return getattr(contract.functions, name)().call(block_identifier=block_number)


def confirm_deployment(w3, transaction_hash, plan, abi):
    if type(w3.eth.chain_id) is not int or w3.eth.chain_id != CHAIN_ID:
        raise ValueError('BSC mainnet chain 56 required')
    if not isinstance(transaction_hash, str) or re.fullmatch(r'0x[0-9a-fA-F]{64}', transaction_hash) is None:
        raise ValueError('Invalid transaction hash')
    transaction_hash = Web3.to_hex(hexstr=transaction_hash)
    transaction = w3.eth.get_transaction(transaction_hash)
    receipt = w3.eth.get_transaction_receipt(transaction_hash)
    if receipt is None or transaction is None:
        raise ValueError('Deployment transaction is unavailable')
    if (
        receipt['status'] != 1
        or receipt['to'] is not None
        or transaction['to'] is not None
        or Web3.to_checksum_address(transaction['from']) != EXPECTED_DEPLOYER
        or transaction['value'] != 0
        or Web3.to_hex(transaction['input']).lower() != plan['deployment_data'].lower()
        or receipt['contractAddress'] is None
        or list(receipt['logs'])
    ):
        raise ValueError('Deployment transaction differs from approved plan')

    finalized = w3.eth.get_block('finalized')
    if receipt['blockNumber'] > finalized['number']:
        raise ValueError('Deployment is not finalized')
    block = w3.eth.get_block(receipt['blockNumber'])
    if block['hash'] != receipt['blockHash']:
        raise ValueError('Deployment receipt is not canonical')
    address = Web3.to_checksum_address(receipt['contractAddress'])
    runtime = w3.eth.get_code(address, block_identifier=finalized['number'])
    runtime_hash = Web3.to_hex(Web3.keccak(runtime))
    if runtime_hash.lower() != plan['expected_runtime_keccak256'].lower():
        raise ValueError('Deployed runtime differs from approved plan')

    contract = w3.eth.contract(address=address, abi=abi)
    values = {
        'agent_id_registry': _read(contract, 'agentIdRegistry', finalized['number']),
        'bsc_agent_id_registry': _read(contract, 'BSC_AGENT_ID_REGISTRY', finalized['number']),
        'bsc_mainnet_chain_id': _read(contract, 'BSC_MAINNET_CHAIN_ID', finalized['number']),
        'receipt_count': _read(contract, 'receiptCount', finalized['number']),
        'unique_agent_count': _read(contract, 'uniqueAgentCount', finalized['number']),
    }
    if (
        Web3.to_checksum_address(values['agent_id_registry']) != OFFICIAL_REGISTRY
        or Web3.to_checksum_address(values['bsc_agent_id_registry']) != OFFICIAL_REGISTRY
        or values['bsc_mainnet_chain_id'] != CHAIN_ID
        or values['receipt_count'] != 0
        or values['unique_agent_count'] != 0
    ):
        raise ValueError('Deployed contract state differs from approved initialization')
    if w3.eth.get_block(finalized['number'])['hash'] != finalized['hash']:
        raise ValueError('Finalized observation changed')

    gas_used = receipt['gasUsed']
    effective_gas_price = receipt['effectiveGasPrice']
    return {
        'status': 'MVP_MAINNET_DEPLOYMENT_CONFIRMED',
        'assurance': 'RPC_FINALIZED_READ',
        'chain_id': CHAIN_ID,
        'transaction_hash': transaction_hash,
        'deployer': EXPECTED_DEPLOYER,
        'contract_address': address,
        'deployment_block_number': receipt['blockNumber'],
        'deployment_block_hash': Web3.to_hex(receipt['blockHash']),
        'finalized_observation_block': finalized['number'],
        'finalized_observation_hash': Web3.to_hex(finalized['hash']),
        'deployment_data_keccak256': Web3.to_hex(Web3.keccak(hexstr=plan['deployment_data'])),
        'runtime_code_keccak256': runtime_hash,
        **values,
        'gas_used': gas_used,
        'effective_gas_price_wei': effective_gas_price,
        'actual_gas_cost_wei': gas_used * effective_gas_price,
        'native_value_wei': 0,
        'logs_count': 0,
        'transactions_sent_by_verifier': 0,
        'bscscan_url': f'https://bscscan.com/address/{address}',
        'limitations': 'Provider-trusted finalized receipt/code/state reads; source verification is a separate step',
    }
