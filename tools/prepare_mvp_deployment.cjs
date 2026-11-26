// Build an offline, unsigned BSC deployment and BscScan verification package.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '..');
const sourceName = 'contracts/VeriAbstainEvidenceRegistry.sol';
const contractName = 'VeriAbstainEvidenceRegistry';
const fullyQualifiedName = `${sourceName}:${contractName}`;
const officialRegistry = '0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F';
const compilerVersion = 'v0.8.28+commit.7893614a';
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const keccak256 = value => {
  const ethers = require(path.join(root, 'verification', 'wallet-tests', 'node_modules', 'ethers'));
  return ethers.keccak256(value);
};

function loadSolc() {
  const candidates = [
    path.join(root, 'verification', 'node_modules', 'solc'),
    path.join(root, '.research', 'source-build', 'node_modules', 'solc'),
  ];
  const selected = candidates.find(candidate => fs.existsSync(candidate));
  if (!selected) throw new Error('Install verification dependencies with npm ci');
  return require(selected);
}

function jsonBytes(value) {
  return Buffer.from(JSON.stringify(value, null, 2) + '\n', 'utf8');
}

function linkImmutableRuntime(unlinkedBytecode, references, address) {
  const identifiers = Object.keys(references || {});
  if (identifiers.length !== 1) throw new Error('Unexpected immutable layout');
  const runtime = Buffer.from(unlinkedBytecode.slice(2), 'hex');
  const replacement = Buffer.from('00'.repeat(12) + address.slice(2).toLowerCase(), 'hex');
  const entries = references[identifiers[0]];
  if (!Array.isArray(entries) || entries.length === 0) throw new Error('Missing immutable references');
  for (const entry of entries) {
    if (
      entry.length !== 32 || entry.start < 0 || entry.start + entry.length > runtime.length ||
      runtime.subarray(entry.start, entry.start + entry.length).some(value => value !== 0)
    ) {
      throw new Error('Unsupported immutable reference');
    }
    replacement.copy(runtime, entry.start);
  }
  return {bytecode: '0x' + runtime.toString('hex'), referenceCount: entries.length};
}

function preparePackage() {
  const solc = loadSolc();
  if (!solc.version().startsWith('0.8.28+commit.7893614a')) {
    throw new Error('Unexpected Solidity compiler');
  }
  const source = fs.readFileSync(path.join(root, sourceName), 'utf8');
  const testedBuildBytes = fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'contract-build.json'));
  const testedBuild = JSON.parse(testedBuildBytes);
  const settings = testedBuild.settings;
  if (
    settings.evmVersion !== 'paris' ||
    settings.optimizer?.enabled !== true ||
    settings.optimizer?.runs !== 200
  ) {
    throw new Error('Tested compiler settings changed');
  }
  const standardInput = {
    language: 'Solidity',
    sources: {[sourceName]: {content: source}},
    settings,
  };
  const compiled = JSON.parse(solc.compile(JSON.stringify(standardInput)));
  const errors = (compiled.errors || []).filter(item => item.severity === 'error');
  if (errors.length) throw new Error(errors.map(item => item.formattedMessage).join('\n'));
  const contract = compiled.contracts[sourceName][contractName];
  const bytecode = '0x' + contract.evm.bytecode.object;
  const deployedBytecode = '0x' + contract.evm.deployedBytecode.object;
  const tested = testedBuild.contracts[contractName];
  if (bytecode !== tested.bytecode || deployedBytecode !== tested.deployedBytecode) {
    throw new Error('Current source does not match the tested contract build');
  }
  const linkedRuntime = linkImmutableRuntime(
    deployedBytecode,
    contract.evm.deployedBytecode.immutableReferences,
    officialRegistry
  );

  const constructorArguments = officialRegistry.slice(2).toLowerCase().padStart(64, '0');
  const deploymentData = bytecode + constructorArguments;
  const initCodeBytes = (deploymentData.length - 2) / 2;
  const runtimeBytes = (deployedBytecode.length - 2) / 2;
  if (initCodeBytes > 49_152 || runtimeBytes > 24_576) {
    throw new Error('Contract exceeds EVM code-size limits');
  }
  const plan = {
    schema_version: 1,
    chain_id: 56,
    contract: fullyQualifiedName,
    compiler_version: compilerVersion,
    evm_version: 'paris',
    optimizer: {enabled: true, runs: 200},
    constructor: {
      signature: 'constructor(address agentIdRegistry_)',
      arguments: [officialRegistry],
      abi_encoded_hex: constructorArguments,
    },
    deployment_data: deploymentData,
    deployment_data_keccak256: keccak256(deploymentData),
    unlinked_runtime_keccak256: keccak256(deployedBytecode),
    expected_runtime_keccak256: keccak256(linkedRuntime.bytecode),
    immutable_reference_count: linkedRuntime.referenceCount,
    init_code_bytes: initCodeBytes,
    runtime_bytes: runtimeBytes,
    native_value_wei: 0,
    deployer: null,
    nonce: null,
    expected_contract_address: null,
    signed_transaction: null,
    transactions_sent: 0,
    warning: 'UNSIGNED_OFFLINE_PLAN_NOT_A_DEPLOYMENT',
  };
  const standardInputBytes = jsonBytes(standardInput);
  const planBytes = jsonBytes(plan);
  const manifest = {
    schema_version: 1,
    explorer: 'BscScan',
    verification_method: 'Solidity (Standard-Json-Input)',
    chain_id: 56,
    contract: fullyQualifiedName,
    compiler_version: compilerVersion,
    license_identifier: 'MIT',
    constructor_arguments_abi_hex: constructorArguments,
    source_sha256: sha256(source),
    tested_build_sha256: sha256(testedBuildBytes),
    standard_input_sha256: sha256(standardInputBytes),
    deployment_plan_sha256: sha256(planBytes),
    contract_address: null,
    verification_submitted: false,
    api_key_required_to_submit: true,
    credentials_stored: false,
    transactions_sent: 0,
  };
  return {
    standardInputBytes,
    planBytes,
    manifestBytes: jsonBytes(manifest),
    plan,
    manifest,
    linkedRuntimeBytecode: linkedRuntime.bytecode,
  };
}

function writePackage(directory) {
  const prepared = preparePackage();
  const destination = path.resolve(directory);
  fs.mkdirSync(destination, {recursive: true});
  const names = ['standard-input.json', 'deployment-plan.json', 'verification-manifest.json'];
  if (names.some(name => fs.existsSync(path.join(destination, name)))) {
    throw new Error('Deployment package output already exists');
  }
  for (const [name, bytes] of [
    [names[0], prepared.standardInputBytes],
    [names[1], prepared.planBytes],
    [names[2], prepared.manifestBytes],
  ]) {
    const file = fs.openSync(path.join(destination, name), 'wx');
    try {
      fs.writeFileSync(file, bytes);
      fs.fsyncSync(file);
    } finally {
      fs.closeSync(file);
    }
  }
  return prepared;
}

function main(argv) {
  if (argv.length !== 2 || argv[0] !== '--output') {
    process.stderr.write('{"status":"INVALID_ARGUMENTS"}\n');
    return 2;
  }
  try {
    const prepared = writePackage(argv[1]);
    process.stdout.write(JSON.stringify({
      status: 'MVP_DEPLOYMENT_PACKAGE_PREPARED',
      output: argv[1],
      deploymentDataKeccak256: prepared.plan.deployment_data_keccak256,
      expectedRuntimeKeccak256: prepared.plan.expected_runtime_keccak256,
      transactionsSent: 0,
    }) + '\n');
    return 0;
  } catch {
    process.stderr.write('{"status":"MVP_DEPLOYMENT_PACKAGE_FAILED"}\n');
    return 2;
  }
}

module.exports = {preparePackage, writePackage, main};
if (require.main === module) process.exitCode = main(process.argv.slice(2));
