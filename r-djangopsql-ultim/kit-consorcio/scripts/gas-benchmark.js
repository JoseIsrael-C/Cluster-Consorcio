// Gas per function for D1 (prototype structure), D2 (proposed) and D3 (hash registry), Table VI.
// Each function is executed RUNS times with distinct certificates; one warm-up call per function
// is excluded so that one-off slot initialisations (first counter/balance write) do not skew the mean.
//   npx hardhat run scripts/gas-benchmark.js                  (Hardhat Network, London rules)
//   npx hardhat run scripts/gas-benchmark.js --network besu   (same benchmark on the QBFT network)
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { ethers } = hre;

const RUNS = Number(process.env.RUNS || 30);
const h = (s) => ethers.keccak256(ethers.toUtf8Bytes(s));

function stats(xs) {
  const n = xs.length;
  const mean = xs.reduce((a, b) => a + b, 0) / n;
  const sd = n > 1 ? Math.sqrt(xs.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1)) : 0;
  return { n, mean, sd, min: Math.min(...xs), max: Math.max(...xs) };
}

async function gasOf(txPromise) {
  const tx = await txPromise;
  const r = await tx.wait();
  return Number(r.gasUsed);
}

async function deployGas(name, args, from) {
  const f = await ethers.getContractFactory(name, from);
  const c = await f.deploy(...args);
  const r = await c.deploymentTransaction().wait();
  return { contract: c, gas: Number(r.gasUsed) };
}

async function main() {
  const signers = await ethers.getSigners();
  const campuses = signers.slice(0, 5);
  const founders = [campuses.map((s) => s.address), [1, 2, 3, 4, 5], [1, 2, 3, 4, 5].map((i) => ethers.keccak256(ethers.toUtf8Bytes(`x509-campus-${i}`)))];
  const [c1, c2] = campuses;
  const raw = {};
  let prototypeGasLimit = null;
  const record_ = (design, fn, xs) => {
    raw[design] = raw[design] || {};
    raw[design][fn] = xs;
    const s = stats(xs);
    console.log(`${design.padEnd(3)} ${fn.padEnd(15)} ${Math.round(s.mean).toString().padStart(9)} ± ${s.sd.toFixed(1)}`);
  };

  // ---------------- D2 proposed and D3 registry (same flow) ----------------
  for (const [design, name] of [["D2", "CertificateConsortium"], ["D3", "HashRegistry"]]) {
    const deploys = [];
    for (let i = 0; i < RUNS; i++) deploys.push((await deployGas(name, founders, c1)).gas);
    record_(design, "deployment", deploys);

    const { contract: c } = await deployGas(name, founders, c1);
    const tag = `${design}-bench`; // fixed tags: identical results on every run
    await gasOf(c.connect(c1).issue(h(`${tag}-warmup`), 1));

    const issue = [];
    for (let i = 0; i < RUNS; i++) issue.push(await gasOf(c.connect(c1).issue(h(`${tag}-issue-${i}`), 1)));
    record_(design, "issue", issue);
    const ids = Array.from({ length: RUNS }, (_, i) => i + 2); // id 1 is the warm-up certificate

    await gasOf(c.connect(c1).recordTransfer(1, 2)); // warm-up
    const transfer = [];
    for (const id of ids) transfer.push(await gasOf(c.connect(c1).recordTransfer(id, 2)));
    record_(design, "recordTransfer", transfer);

    await gasOf(c.connect(c1).revoke(1)); // warm-up
    const revoke = [];
    for (const id of ids) revoke.push(await gasOf(c.connect(c1).revoke(id)));
    record_(design, "revoke", revoke);

    if (design === "D2") {
      const base = Number(await c.connect(c1).issue.staticCall(h(`${tag}-probe`), 1));
      for (let i = 0; i <= RUNS; i++) await gasOf(c.connect(c1).issue(h(`${tag}-tobereissued-${i}`), 1));
      await gasOf(c.connect(c1).reissue(base, h(`${tag}-reissued-warmup`), 1)); // warm-up
      const reissue = [];
      for (let i = 1; i <= RUNS; i++) {
        reissue.push(await gasOf(c.connect(c1).reissue(base + i, h(`${tag}-reissued-${i}`), 1)));
      }
      record_(design, "reissue", reissue);
    }
  }

  // ---------------- D1: the earlier prototype contract (CertificadosContract.sol, verbatim) ----------------
  // Called as the prototype's Django views call it (see scripts/prototype-data.js). The prototype sends
  // emitirCertificado with a fixed gas limit of 300,000 (management/contrato.py), so we also count how
  // many issuances would exceed it.
  {
    const { record } = require("./prototype-data");
    const deploys = [];
    for (let i = 0; i < RUNS; i++) deploys.push((await deployGas("CertificadosContract", [], c1)).gas);
    record_("D1", "deployment", deploys);
    const { contract: d1 } = await deployGas("CertificadosContract", [], c1);
    await gasOf(d1.emitirCertificado(...record(999).A)); // warm-up
    const issueA = [];
    for (let i = 0; i < RUNS; i++) issueA.push(await gasOf(d1.emitirCertificado(...record(i).A)));
    record_("D1", "issueDocument", issueA); // document certificate: name, CURP, enrollment no., program, title
    const issueB = [];
    for (let i = 0; i < RUNS; i++) issueB.push(await gasOf(d1.emitirCertificado(...record(i).B)));
    record_("D1", "issue", issueB); // certificate form: name parts, enrollment no., course (as measured in [10])
    await gasOf(d1.revocarCertificado(record(999).A[0])); // warm-up
    const revoke = [];
    for (let i = 0; i < RUNS; i++) revoke.push(await gasOf(d1.revocarCertificado(record(i).A[0])));
    record_("D1", "revoke", revoke);
    prototypeGasLimit = {
      limit: 300000,
      issueAbove: issueA.filter((g) => g > 300000).length,
      issueBAbove: issueB.filter((g) => g > 300000).length,
      runs: RUNS,
    };
    console.log(`D1 issuances above the prototype's 300,000 gas limit: ${prototypeGasLimit.issueAbove}/${RUNS} (pattern A), ${prototypeGasLimit.issueBAbove}/${RUNS} (pattern B)`);
  }

  const summary = {};
  for (const [d, fns] of Object.entries(raw)) {
    summary[d] = {};
    for (const [fn, xs] of Object.entries(fns)) summary[d][fn] = stats(xs);
  }
  const out = path.join(__dirname, "..", "results");
  fs.mkdirSync(out, { recursive: true });
  const net = hre.network.name;
  fs.writeFileSync(
    path.join(out, `gas-${net}.json`),
    JSON.stringify({ network: net, runs: RUNS, warmupExcluded: true, d1: "contracts/prototype/CertificadosContract.sol (verbatim)", prototypeGasLimit, summary, raw }, null, 2),
  );
  const rows = ["design,function,n,mean,sd,min,max"];
  for (const [d, fns] of Object.entries(summary))
    for (const [fn, s] of Object.entries(fns)) rows.push([d, fn, s.n, s.mean.toFixed(1), s.sd.toFixed(1), s.min, s.max].join(","));
  fs.writeFileSync(path.join(out, `gas-${net}.csv`), rows.join("\n") + "\n");
  console.log(`\nSaved results/gas-${net}.json and .csv`);
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
