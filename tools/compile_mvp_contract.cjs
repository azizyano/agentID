// Compile the MVP contracts locally. No wallet, RPC, signing, or deployment.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '..');
const solcCandidates = [
  path.join(root, 'verification', 'node_modules', 'solc'),
  path.join(root, '.research', 'source-build', 'node_modules', 'solc'),
];
const solcPath = solcCandidates.find(candidate => fs.existsSync(candidate));
if (!solcPath) throw new Error('Install verification dependencies with npm ci');
const solc = require(solcPath);
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');

const sources = {};
for (const name of [
  'contracts/VeriAbstainEvidenceRegistry.sol',
  'contracts/test/MockAgentIdRegistry.sol',
]) {
  sources[name] = {content: fs.readFileSync(path.join(root, name), 'utf8')};
}

const settings = {
  evmVersion: 'paris',
  optimizer: {enabled: true, runs: 200},
  outputSelection: {'*': {'*': ['abi', 'evm.bytecode', 'evm.deployedBytecode']}},
};
const output = JSON.parse(solc.compile(JSON.stringify({language: 'Solidity', sources, settings})));
const errors = (output.errors || []).filter(item => item.severity === 'error');
if (errors.length) throw new Error(errors.map(item => item.formattedMessage).join('\n'));

function artifact(source, name) {
  const contract = output.contracts[source][name];
  return {
    contractName: name,
    sourceName: source,
    abi: contract.abi,
    bytecode: '0x' + contract.evm.bytecode.object,
    deployedBytecode: '0x' + contract.evm.deployedBytecode.object,
  };
}

const result = {
  compiler: solc.version(),
  settings,
  sourceSha256: Object.fromEntries(
    Object.entries(sources).map(([name, item]) => [name, sha256(item.content)])
  ),
  contracts: {
    VeriAbstainEvidenceRegistry: artifact(
      'contracts/VeriAbstainEvidenceRegistry.sol',
      'VeriAbstainEvidenceRegistry'
    ),
    MockAgentIdRegistry: artifact(
      'contracts/test/MockAgentIdRegistry.sol',
      'MockAgentIdRegistry'
    ),
  },
};

const destination = path.join(root, 'artifacts', 'mvp');
fs.mkdirSync(destination, {recursive: true});
fs.writeFileSync(
  path.join(destination, 'contract-build.json'),
  JSON.stringify(result, null, 2) + '\n'
);
console.log(JSON.stringify({
  status: 'MVP_CONTRACT_COMPILED',
  compiler: result.compiler,
  sourceSha256: result.sourceSha256,
  runtimeBytes: (result.contracts.VeriAbstainEvidenceRegistry.deployedBytecode.length - 2) / 2,
}));
