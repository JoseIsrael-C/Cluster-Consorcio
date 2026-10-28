// Builds results/RESULTS.md with every value requested by the paper (abstract, Tables IV–VII).
const fs = require("fs");
const path = require("path");

const R = path.join(__dirname, "..", "results");
const read = (f) => {
  try {
    return JSON.parse(fs.readFileSync(path.join(R, f), "utf8"));
  } catch {
    return null;
  }
};
const txt = (f) => {
  try {
    return fs.readFileSync(path.join(R, f), "utf8");
  } catch {
    return "";
  }
};
const n0 = (x) => (x == null ? "—" : Math.round(x).toLocaleString("en-US"));
const f = (x, d = 2) => (x == null || Number.isNaN(x) ? "—" : x.toFixed(d));
const out = [];

// ---- tests
const testsTxt = txt("tests.txt");
const passing = Number((testsTxt.match(/(\d+) passing/) || [])[1] || 0);
const failing = Number((testsTxt.match(/(\d+) failing/) || [])[1] || 0);
const tPass = new Set([...testsTxt.matchAll(/(?:✔|✓)\s+T(\d+)\b/g)].map((m) => Number(m[1])));
const cov = read("coverage-summary.json");
const sl = read("slither.json");
out.push("# Results for integration\n");
out.push("## Table V · tests, coverage, static analysis\n");
out.push(`- Tests T1–T${tPass.size} passing: **${tPass.size} of ${tPass.size}** (whole suite: ${passing} passing, ${failing} failing)`);
for (let t = 1; t <= 17; t++) out.push(`  - T${t}: ${tPass.has(t) ? "pass" : "FAIL / not run"}`);
const pbt = testsTxt.match(/model-based tests: \d+ calls.*/);
const pbtPass = [...testsTxt.matchAll(/(?:✔|✓)\s+P1–P7 hold/g)].length;
if (pbt) out.push(`- Model-based governance tests: ${pbtPass} sequences passing; ${pbt[0].replace("model-based tests: ", "")}`);
const vt = read("verifier-test.json");
if (vt) out.push(`- Reference verifier and gateway (python verifier/test_verifier.py): ${vt.filter((c) => c.asExpected).length} of ${vt.length} cases as expected`);
if (cov) {
  out.push(`- Coverage (CertificateConsortium.sol + ConsortiumGovernance.sol): lines **${f(cov.total.lines.pct, 1)} %**, branches **${f(cov.total.branches.pct, 1)} %**, functions ${f(cov.total.functions.pct, 1)} %, statements ${f(cov.total.statements.pct, 1)} %`);
  for (const [file, v] of Object.entries(cov)) {
    if (file === "total") continue;
    out.push(`  - ${path.basename(file)}: lines ${f(v.lines.pct, 1)} %, branches ${f(v.branches.pct, 1)} %`);
  }
}
if (sl && sl.results) {
  const dets = sl.results.detectors || [];
  const scope = (d) =>
    (d.elements || []).some((e) => /contracts\/(CertificateConsortium|ConsortiumGovernance|IERC5192)\.sol/.test(e?.source_mapping?.filename_relative || ""));
  const by = (list) => list.reduce((a, d) => ((a[d.impact] = (a[d.impact] || 0) + 1), a), {});
  const inScope = dets.filter(scope);
  out.push(`- Slither: ${dets.length} findings in all kit contracts ${JSON.stringify(by(dets))}; **${inScope.length} in D2 + governance** ${JSON.stringify(by(inScope))}`);
  for (const d of inScope) out.push(`  - [${d.impact}/${d.confidence}] ${d.check}: ${(d.description || "").split("\n")[0].slice(0, 180)}`);
} else out.push("- Slither: not run (see results/logs/slither.log)");

// ---- gas
const gas = read("gas-hardhat.json");
if (gas) {
  const s = gas.summary;
  const cell = (d, fn) => (s[d] && s[d][fn] ? `${n0(s[d][fn].mean)} ± ${f(s[d][fn].sd, 1)}` : "—");
  out.push("\n## Table VI · gas per function, mean ± SD over " + gas.runs + " runs (Hardhat Network, London rules, warm-up excluded)\n");
  out.push("| Function | D1 prototype | D2 proposed | D3 registry |\n|---|---|---|---|");
  for (const fn of ["issue", "recordTransfer", "revoke", "reissue", "deployment"])
    out.push(`| ${fn} | ${cell("D1", fn)} | ${cell("D2", fn)} | ${cell("D3", fn)} |`);
  const g = (d, fn) => s[d]?.[fn]?.mean;
  const red = (a, b) => (a && b ? (100 * (a - b)) / a : null);
  out.push("");
  out.push(`- issue: D2 vs D1 ${f(red(g("D1", "issue"), g("D2", "issue")), 1)} % (${n0(g("D1", "issue"))} → ${n0(g("D2", "issue"))}); token-layer overhead D2 − D3 = ${n0(g("D2", "issue") - g("D3", "issue"))} gas (+${f((100 * (g("D2", "issue") - g("D3", "issue"))) / g("D3", "issue"), 1)} %)`);
  out.push(`- recordTransfer: D2 vs D1 ${f(red(g("D1", "recordTransfer"), g("D2", "recordTransfer")), 1)} %; revoke: D2 vs D1 ${f(red(g("D1", "revoke"), g("D2", "revoke")), 1)} %`);
  out.push(`- deployment: D2 − D3 = ${n0(g("D2", "deployment") - g("D3", "deployment"))} gas (ERC-721/ERC-5192 code)`);
  out.push(`- Abstract: issuance uses **[X] = ${n0(g("D2", "issue"))}** gas instead of **[Y] = ${n0(g("D1", "issue"))}**`);
}

// ---- network
const nw = read("network.json");
if (nw) {
  const S = nw.scenarios;
  const row = (k, label) => {
    const m = S[k];
    if (!m) return `| ${label} | — | — | — | — |`;
    return `| ${label} | ${f(m.tps)} | ${f(m.latency.p50)} | ${f(m.latency.p95)} | ${f(m.confirmedPct, 1)} % (${m.confirmed}/${m.submitted}) |`;
  };
  out.push("\n## Table VII · last single run, results/network.json (5 validators, 2 s blocks)\n");
  out.push("| Scenario | TPS | p50 (s) | p95 (s) | Confirmed |\n|---|---|---|---|---|");
  out.push(row("S1", `S1 steady, ${nw.rate} tx/s`));
  out.push(row("S2", "S2 burst of 60"));
  out.push(row("S3", "S3 one validator down"));
  if (S.S4) {
    const o = S.S4.duringOutage;
    out.push(`| S4 two validators down | 0 | — | — | ${f(o.confirmedPct, 1)} % (${o.confirmed}/${S.S4.submitted}) during a ${f(o.outageS, 0)} s outage; ${o.blocksProduced} blocks |`);
  }
  if (S.S5) out.push(`| S5 verification (read) | — | ${f(S.S5.latency.p50, 4)} | ${f(S.S5.latency.p95, 4)} | — |`);
  out.push("");
  if (S.S4) {
    const r = S.S4.recovery;
    out.push(`- S4 recovery: block production resumed **${f(r.resumeAfterRestartS, 1)} s** after restarting the fourth validator (its RPC answered at ${f(r.node3RpcUpS, 1)} s); afterwards ${r.confirmedAfterRecovery} of the ${S.S4.submitted} queued transactions were confirmed (${f(r.confirmedAfterRecoveryPct, 1)} % in total).`);
  }
  if (S.S3) out.push(`- S3: mean block interval ${f(S.S3.blocks.meanIntervalS)} s (max ${S.S3.blocks.maxIntervalS} s) vs S1 ${f(S.S1?.blocks.meanIntervalS)} s; validator 4 resynchronised ${f(S.S3.rejoinSyncS, 1)} s after restart.`);
  if (S.S1) out.push(`- S1 blocks: ${f(S.S1.blocks.meanTxPerBlock, 1)} tx/block on average (max ${S.S1.blocks.maxTxPerBlock}); issue gas on Besu (receipts, n=${S.S1.issueGas.n}): ${n0(S.S1.issueGas.mean)} ± ${f(S.S1.issueGas.sd, 1)}, reverted ${S.S1.issueGas.reverted}.`);
  out.push(`- D2 deployment on Besu: ${n0(nw.deploymentGas)} gas`);
  if (S.S1) out.push(`- Abstract: **[Z] = ${f(S.S1.tps, 1)} tx/s** sustained; **[W] = ${f(S.S1.latency.p50, 2)} s** median confirmation latency (S1)`);
}

// ---- medians over several runs (scripts/aggregate-runs.js)
const agg = read("network-summary.json");
if (agg) {
  const S = agg.scenarios;
  const m = (s, d = 2) => `${f(s.median, d)} [${f(s.min, d)}–${f(s.max, d)}]`;
  out.push(`\n## Table VII · median [min–max] over ${agg.runs.length} runs (values used in the paper)\n`);
  out.push("| Scenario | TPS | p50 (s) | p95 (s) | Confirmed |\n|---|---|---|---|---|");
  for (const [k, label] of [["S1", "S1 steady, 20 tx/s"], ["S2", "S2 burst of 60"], ["S3", "S3 one validator down"]])
    out.push(`| ${label} | ${m(S[k].tps)} | ${m(S[k].p50)} | ${m(S[k].p95)} | ${f(S[k].confirmedPct.median, 0)} % |`);
  out.push(`| S4 two validators down | 0 | — | — | ${f(S.S4.confirmedDuringOutagePct.median, 0)} % during a ${f(S.S4.outageS.median, 0)} s outage |`);
  out.push(`| S5 verification (read) | — | ${m(S.S5.p50, 4)} | ${m(S.S5.p95, 4)} | — |`);
  out.push(`\n- S4: blocks resumed ${m(S.S4.resumeAfterRestartS, 1)} s after restarting the fourth validator; ${f(S.S4.confirmedAfterRecoveryPct.median, 0)} % of the queued transactions confirmed afterwards.`);
  out.push(`- Issue gas from Besu receipts: ${m(agg.issueGasBesu, 1)}`);
  out.push(`- Runs: ${agg.runs.map((r) => r.dir).join(", ")}`);
  out.push(`- Abstract: **[Z] = ${f(S.S1.tps.median, 1)} tx/s**, **[W] = ${f(S.S1.p50.median, 2)} s**`);
}

// ---- Raspberry Pi 4B emulation (scripts/throttle.js)
const cals = (agg ? agg.runs.map((r) => r.dir) : [])
  .map((d) => { try { return JSON.parse(fs.readFileSync(path.join(R, "..", d, "pi-calibration.json"), "utf8")); } catch { return null; } })
  .filter(Boolean);
if (cals.length) {
  out.push("\n## Raspberry Pi 4B emulation (calibration per run)\n");
  out.push(`Target: Geekbench 6 single-core 287 (Pi 4B, 1.8 GHz) / 4,263 (Apple M5) = ${f(287 / 4263, 4)} of native speed; JVM -Xmx1536m -XX:ActiveProcessorCount=4.\n`);
  out.push("| Run | commanded duty | achieved speed ratio | GB6 single-core equivalent |\n|---|---|---|---|");
  agg.runs.forEach((r, i) => cals[i] && out.push(`| ${r.dir} | ${f(cals[i].onFactor, 3)} | ${f(cals[i].achievedSpeedRatio, 4)} | ${cals[i].equivalentGeekbench6SingleCore} |`));
}

// ---- earlier prototype executed with its own integration code (scripts/run_prototype_integration.py)
const pi = read("prototype-integration.json");
if (pi) {
  const A = pi.calls.emitir_certificado_patternA, B = pi.calls.emitir_certificado_patternB;
  out.push("\n## Earlier prototype (contrato.py unmodified, Web3.py " + pi.web3 + ")\n");
  out.push(`- Deployment: ${pi.deploymentGas.toLocaleString("en-US")} gas`);
  out.push(`- emitir_certificado, form record (pattern B): ${Math.round(B.mean).toLocaleString("en-US")} ± ${f(B.sd, 0)} gas, ${B.n}/30 succeeded`);
  out.push(`- emitir_certificado, document record with CURP (pattern A): ${A.failed} of 30 failed out of gas under the fixed 300,000 limit (successful ones: ${Math.round(A.mean).toLocaleString("en-US")} ± ${f(A.sd, 0)} gas)`);
  for (const [k, v] of Object.entries(pi.errors || {})) out.push(`- ${k}: fails — ${String(v).split(":")[0]}${/rawTransaction/.test(v) ? " (rawTransaction attribute removed in current Web3.py)" : /out of gas/.test(v) ? " (out of gas under the fixed limit)" : ""}`);
}

// ---- environment
const env = read("environment.json");
if (env) {
  out.push("\n## Table IV · environment\n");
  out.push(`| Host (CPU, RAM, OS) | ${env.host.cpu}, ${env.host.cores} cores, ${env.host.ramGB} GB RAM, ${env.host.os} |`);
  out.push(`| Node.js / Hardhat / ethers | ${env.node} / ${env.hardhat} / ${env.ethers} |`);
  out.push(`| solc / optimizer | ${env.solc.version} / enabled, ${env.solc.settings.optimizer.runs} runs (EVM ${env.solc.settings.evmVersion}) |`);
  out.push(`| OpenZeppelin Contracts | ${env.openzeppelin} |`);
  out.push(`| Hyperledger Besu | ${env.besu}; ${env.java}; QBFT, 2 s blocks, 5 validators + 5 RPC nodes |`);
  out.push(`| solidity-coverage / Slither | ${env.solidityCoverage} / ${env.slither} |`);
}
fs.writeFileSync(path.join(R, "RESULTS.md"), out.join("\n") + "\n");
console.log(out.join("\n"));
