// Export the reviewed one-time MetaMask helper. Does not access a wallet.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '..');
const plan = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'deployment-package', 'deployment-plan.json')));
const preflight = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'mainnet-preflight-7841.json')));
const build = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'contract-build.json')));
const source = fs.readFileSync(path.join(root, 'contracts', 'VeriAbstainEvidenceRegistry.sol'), 'utf8');
const ethers = require(path.join(root, 'verification', 'wallet-tests', 'node_modules', 'ethers'));
const solcCandidates = [
  path.join(root, 'verification', 'node_modules', 'solc'),
  path.join(root, '.research', 'source-build', 'node_modules', 'solc'),
];
const solc = require(solcCandidates.find(candidate => fs.existsSync(candidate)));
const official = '0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F';

function expectedRuntime() {
  const sourceName = 'contracts/VeriAbstainEvidenceRegistry.sol';
  const input = {language: 'Solidity', sources: {[sourceName]: {content: source}}, settings: build.settings};
  const output = JSON.parse(solc.compile(JSON.stringify(input)));
  const contract = output.contracts[sourceName].VeriAbstainEvidenceRegistry;
  const runtime = Buffer.from(contract.evm.deployedBytecode.object, 'hex');
  const references = Object.values(contract.evm.deployedBytecode.immutableReferences || {});
  if (references.length !== 1 || references[0].length !== plan.immutable_reference_count) {
    throw new Error('Unexpected immutable layout');
  }
  const replacement = Buffer.from('00'.repeat(12) + official.slice(2).toLowerCase(), 'hex');
  for (const entry of references[0]) {
    if (entry.length !== 32 || runtime.subarray(entry.start, entry.start + 32).some(value => value !== 0)) {
      throw new Error('Unsupported immutable slot');
    }
    replacement.copy(runtime, entry.start);
  }
  return '0x' + runtime.toString('hex');
}

function exportStep(output) {
  if (
    preflight.status !== 'MAINNET_PREFLIGHT_READY' || preflight.transactions_sent !== 0 ||
    preflight.deployer !== '0xb16b77C16773DEF8fA279A1228Eba9308eCD7841' ||
    preflight.agent_id_registry !== official ||
    preflight.deployment_data_keccak256.toLowerCase() !== plan.deployment_data_keccak256.toLowerCase()
  ) throw new Error('Mainnet preflight does not match the deployment plan');
  const runtime = expectedRuntime();
  if (ethers.keccak256(runtime).toLowerCase() !== plan.expected_runtime_keccak256.toLowerCase()) {
    throw new Error('Expected runtime differs from the reviewed plan');
  }
  const abi = ethers.AbiCoder.defaultAbiCoder();
  const cfg = {
    origin: 'https://bscscan.com',
    chainId: '0x38',
    deployer: preflight.deployer,
    registry: official,
    registryNameResult: abi.encode(['string'], ['SPACE ID Agent ID']),
    registrySymbolResult: abi.encode(['string'], ['AI']),
    deploymentData: plan.deployment_data,
    deploymentDataHash: plan.deployment_data_keccak256,
    expectedRuntime: runtime,
    expectedRuntimeHash: plan.expected_runtime_keccak256,
    maxGasLimit: String(preflight.proposed_gas_limit * 2),
    maxGasPriceWei: String(preflight.gas_price_wei * 10),
    maxNativeCostWei: '1000000000000000',
  };
  const template = fs.readFileSync(path.join(root, 'tools', 'mvp-deploy.template.js'), 'utf8');
  const script = template.replace('__CONFIG__', JSON.stringify(cfg));
  if (!script.includes(plan.deployment_data) || !script.includes(runtime)) throw new Error('Export incomplete');
  fs.writeFileSync(output, script, {encoding: 'utf8', flag: 'wx'});
  return {cfg, scriptSha256: crypto.createHash('sha256').update(script).digest('hex')};
}

function main(argv) {
  if (argv.length !== 2 || argv[0] !== '--output') return 2;
  try {
    const result = exportStep(path.resolve(argv[1]));
    process.stdout.write(JSON.stringify({
      status: 'MVP_METAMASK_STEP_EXPORTED',
      output: argv[1],
      scriptSha256: result.scriptSha256,
      maximumNativeCostWei: result.cfg.maxNativeCostWei,
      transactionsSent: 0,
    }) + '\n');
    return 0;
  } catch {
    process.stderr.write('{"status":"MVP_METAMASK_STEP_EXPORT_FAILED","transactionsSent":0}\n');
    return 2;
  }
}

module.exports = {exportStep, main};
if (require.main === module) process.exitCode = main(process.argv.slice(2));
