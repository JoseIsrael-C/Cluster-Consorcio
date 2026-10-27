require("@nomicfoundation/hardhat-toolbox");
const path = require("path");
const { subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } = require("hardhat/builtin-tasks/task-names");
const { CAMPUS_KEYS } = require("./scripts/keys");

// solc 0.8.24 is taken from the pinned npm package `solc` (solcjs), so compilation is reproducible
// offline and does not depend on binaries.soliditylang.org. Same compiler, same bytecode.
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD, async (args, hre, runSuper) => {
  if (args.solcVersion !== "0.8.24") return runSuper();
  const solc = require("solc");
  return {
    compilerPath: path.join(__dirname, "node_modules", "solc", "soljson.js"),
    isSolcJs: true,
    version: args.solcVersion,
    longVersion: solc.version().replace(".Emscripten.clang", ""),
  };
});

/** Compiler and EVM settings match the Besu genesis (Berlin + London, zero base fee). */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: "paris" },
  },
  networks: {
    hardhat: { hardfork: "london", initialBaseFeePerGas: 0 },
    besu: {
      url: process.env.BESU_RPC || "http://127.0.0.1:8545",
      chainId: 2027,
      accounts: CAMPUS_KEYS,
      gasPrice: 0,
    },
  },
  mocha: { timeout: 120000 },
};
