// Coverage is reported for the proposed contract (D2) and its governance module.
module.exports = {
  skipFiles: ["prototype/CertificadosContract.sol", "HashRegistry.sol", "IERC5192.sol"],
  istanbulReporter: ["html", "lcov", "text", "json-summary"],
};
