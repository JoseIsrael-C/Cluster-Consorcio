// Aggregates several network runs (Table VII): median and range per metric.
//   node scripts/aggregate-runs.js results/runs/<run1> results/runs/<run2> ...
// Writes results/network-summary.json (or the file named by OUT) and prints the table.
const fs = require("fs");
const path = require("path");

const dirs = process.argv.slice(2);
if (!dirs.length) {
  console.error("usage: node scripts/aggregate-runs.js <run dir> [<run dir> ...]");
  process.exit(1);
}
const runs = dirs.map((d) => ({ dir: d, data: JSON.parse(fs.readFileSync(path.join(d, "network.json"), "utf8")) }));
const median = (xs) => {
  const s = xs.filter((x) => x != null).sort((a, b) => a - b);
  if (!s.length) return null;
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const stat = (get) => {
  const xs = runs.map((r) => {
    try {
      return get(r.data);
    } catch {
      return null;
    }
  });
  const v = xs.filter((x) => x != null);
  return { median: median(v), min: v.length ? Math.min(...v) : null, max: v.length ? Math.max(...v) : null, values: xs };
};

const out = { runs: runs.map((r) => ({ dir: r.dir, startedAt: r.data.startedAt })), scenarios: {} };
for (const k of ["S1", "S2", "S3"]) {
  out.scenarios[k] = {
    tps: stat((d) => d.scenarios[k].tps),
    p50: stat((d) => d.scenarios[k].latency.p50),
    p95: stat((d) => d.scenarios[k].latency.p95),
    confirmedPct: stat((d) => d.scenarios[k].confirmedPct),
    submitted: stat((d) => d.scenarios[k].submitted),
    rejectedAtSubmit: stat((d) => d.scenarios[k].rejectedAtSubmit),
    retriedSubmissions: stat((d) => d.scenarios[k].retriedSubmissions ?? 0),
    meanBlockIntervalS: stat((d) => d.scenarios[k].blocks.meanIntervalS),
    maxBlockIntervalS: stat((d) => d.scenarios[k].blocks.maxIntervalS),
    includedByEndOfRun: stat((d) => d.scenarios[k].includedByEndOfRun),
  };
}
out.scenarios.S3.rejoinSyncS = stat((d) => d.scenarios.S3.rejoinSyncS);
out.scenarios.S4 = {
  confirmedDuringOutagePct: stat((d) => d.scenarios.S4.duringOutage.confirmedPct),
  blocksDuringOutage: stat((d) => d.scenarios.S4.duringOutage.blocksProduced),
  outageS: stat((d) => d.scenarios.S4.duringOutage.outageS),
  resumeAfterRestartS: stat((d) => d.scenarios.S4.recovery.resumeAfterRestartS),
  node3RpcUpS: stat((d) => d.scenarios.S4.recovery.node3RpcUpS),
  confirmedAfterRecoveryPct: stat((d) => d.scenarios.S4.recovery.confirmedAfterRecoveryPct),
  submitted: stat((d) => d.scenarios.S4.submitted),
};
out.scenarios.S5 = {
  p50: stat((d) => d.scenarios.S5.latency.p50),
  p95: stat((d) => d.scenarios.S5.latency.p95),
  validPct: stat((d) => (100 * d.scenarios.S5.returnedValid) / d.scenarios.S5.calls),
  callErrors: stat((d) => d.scenarios.S5.callErrors ?? 0),
};
out.issueGasBesu = stat((d) => d.scenarios.S1.issueGas.mean);
out.issueGasBesuSd = stat((d) => d.scenarios.S1.issueGas.sd);
out.deploymentGasBesu = stat((d) => d.deploymentGas);

out.interCampusLatencyMs = stat((d) => d.interCampusLatencyMs ?? 0);
// S6 saturation ramp (runs that have it): per offered rate, median throughput and latency, and how many runs saturated.
const rampRuns = runs.filter((r) => r.data.scenarios.S6);
if (rampRuns.length) {
  const rates = [...new Set(rampRuns.flatMap((r) => r.data.scenarios.S6.steps.map((m) => m.offered)))].sort((a, b) => a - b);
  const stepOf = (d, rate) => d.scenarios.S6.steps.find((m) => m.offered === rate);
  out.scenarios.S6 = {
    runs: rampRuns.length,
    steps: rates.map((rate) => ({
      offered: rate,
      runsWithStep: rampRuns.filter((r) => stepOf(r.data, rate)).length,
      steadyTps: stat((d) => stepOf(d, rate).steadyTps),
      submitRate: stat((d) => stepOf(d, rate).submitRate),
      p50: stat((d) => stepOf(d, rate).latency.p50),
      p95: stat((d) => stepOf(d, rate).latency.p95),
      confirmedPct: stat((d) => stepOf(d, rate).confirmedPct),
      rejectedAtSubmit: stat((d) => stepOf(d, rate).rejectedAtSubmit),
      meanBlockIntervalS: stat((d) => stepOf(d, rate).blocks.meanIntervalS),
      meanTxPerBlock: stat((d) => stepOf(d, rate).blocks.meanTxPerBlock),
      saturatedRuns: rampRuns.filter((r) => stepOf(r.data, rate)?.saturated).length,
      harnessLimitedRuns: rampRuns.filter((r) => stepOf(r.data, rate)?.harnessLimited).length,
    })),
    maxSustainedOffered: stat((d) => d.scenarios.S6.maxSustainedOffered),
    firstSaturatedOffered: stat((d) => d.scenarios.S6.firstSaturatedOffered),
    // first step where the network fell behind: confirmed < 90 % of submitted, or the RPC nodes did not accept
    // submissions at 90 % of the offered rate (back-pressure)
    firstLimitedOffered: stat((d) => d.scenarios.S6.firstSaturatedOffered ?? d.scenarios.S6.harnessLimitedAt),
    peakSteadyTps: stat((d) => d.scenarios.S6.peakSteadyTps),
  };
}
fs.writeFileSync(process.env.OUT || path.join(__dirname, "..", "results", "network-summary.json"), JSON.stringify(out, null, 2));
const f = (x, d = 2) => (x == null ? "—" : x.toFixed(d));
const r = (s, d = 2) => `${f(s.median, d)} [${f(s.min, d)}–${f(s.max, d)}]`;
console.log(`Median [min–max] over ${runs.length} runs`);
for (const k of ["S1", "S2", "S3"]) {
  const s = out.scenarios[k];
  console.log(`${k}  TPS ${r(s.tps)}  p50 ${r(s.p50)} s  p95 ${r(s.p95)} s  confirmed ${r(s.confirmedPct, 1)} %  rejected ${r(s.rejectedAtSubmit, 0)}  block interval ${r(s.meanBlockIntervalS)} s (max ${r(s.maxBlockIntervalS, 0)} s)`);
}
const s4 = out.scenarios.S4;
console.log(`S4  confirmed during outage ${r(s4.confirmedDuringOutagePct, 1)} %  resume ${r(s4.resumeAfterRestartS, 1)} s  after recovery ${r(s4.confirmedAfterRecoveryPct, 1)} %`);
console.log(`S5  p50 ${r(out.scenarios.S5.p50, 4)} s  p95 ${r(out.scenarios.S5.p95, 4)} s`);
console.log(`issue gas on Besu ${r(out.issueGasBesu, 1)}`);
if (out.scenarios.S6) {
  for (const st of out.scenarios.S6.steps) {
    console.log(`S6 ${String(st.offered).padStart(3)} tx/s offered  steady-state ${r(st.steadyTps)}  submitted at ${r(st.submitRate)}  p50 ${r(st.p50)} s  p95 ${r(st.p95)} s  confirmed ${r(st.confirmedPct, 1)} %  saturated in ${st.saturatedRuns} of ${st.runsWithStep} runs reaching it`);
  }
  console.log(`S6 sustained up to ${r(out.scenarios.S6.maxSustainedOffered, 0)} tx/s offered; first saturated ${r(out.scenarios.S6.firstSaturatedOffered, 0)}; first limited ${r(out.scenarios.S6.firstLimitedOffered, 0)}; peak steady-state ${r(out.scenarios.S6.peakSteadyTps, 1)} tx/s`);
}
