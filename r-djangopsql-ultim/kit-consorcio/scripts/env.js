// Records the experimental environment (Table IV) in results/environment.json.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execSync } = require("child_process");

const sh = (c) => {
  try {
    return execSync(c, { stdio: ["ignore", "pipe", "pipe"] }).toString().trim();
  } catch (e) {
    return ((e.stdout || "").toString() + (e.stderr || "").toString()).trim() || null;
  }
};
const pkg = (p) => {
  try {
    return JSON.parse(fs.readFileSync(path.join(__dirname, "..", "node_modules", p, "package.json"), "utf8")).version;
  } catch {
    return null;
  }
};

let cpu = os.cpus()[0]?.model;
let osName = `${os.type()} ${os.release()}`;
if (process.platform === "darwin") {
  cpu = sh("sysctl -n machdep.cpu.brand_string") || cpu;
  osName = `macOS ${sh("sw_vers -productVersion")} (${sh("sw_vers -buildVersion")})`;
  const model = sh("sysctl -n hw.model");
  if (model) cpu = `${cpu} · ${model}`;
} else if (fs.existsSync("/etc/os-release")) {
  const m = fs.readFileSync("/etc/os-release", "utf8").match(/PRETTY_NAME="([^"]+)"/);
  if (m) osName = `${m[1]} (kernel ${os.release()})`;
}
const javaOut = sh("java -version 2>&1") || "";
const env = {
  capturedAt: new Date().toISOString(),
  host: { cpu, cores: os.cpus().length, ramGB: +(os.totalmem() / 2 ** 30).toFixed(1), os: osName, arch: process.arch },
  node: process.version,
  hardhat: pkg("hardhat"),
  ethers: pkg("ethers"),
  hardhatToolbox: pkg("@nomicfoundation/hardhat-toolbox"),
  solidityCoverage: pkg("solidity-coverage"),
  openzeppelin: pkg("@openzeppelin/contracts"),
  solc: (() => {
    const cfg = fs.readFileSync(path.join(__dirname, "..", "hardhat.config.js"), "utf8");
    const g = (re) => (cfg.match(re) || [])[1] || null;
    return { version: g(/version:\s*"([^"]+)"/), settings: { optimizer: { runs: Number(g(/runs:\s*(\d+)/)) }, evmVersion: g(/evmVersion:\s*"([^"]+)"/) } };
  })(),
  besu: (sh("besu --version 2>/dev/null") || "").split("\n").find((l) => /besu/i.test(l)) || null,
  java: (javaOut.split("\n").find((l) => /version/.test(l)) || "").trim() || null,
  slither: sh("slither --version 2>/dev/null"),
};
fs.mkdirSync(path.join(__dirname, "..", "results"), { recursive: true });
fs.writeFileSync(path.join(__dirname, "..", "results/environment.json"), JSON.stringify(env, null, 2));
console.log(JSON.stringify(env, null, 2));
