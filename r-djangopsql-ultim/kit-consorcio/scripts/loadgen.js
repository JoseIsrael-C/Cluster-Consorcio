// Network performance scenarios S1–S5 on the 5-validator QBFT network (Table VII).
//   bash network/net.sh start && node scripts/loadgen.js
// Each campus account sends to its own validator (campus i -> RPC 8545+i). Confirmation time is the
// moment the transaction is first seen in a block polled every 100 ms from validator 0, which is never
// stopped. Latency = confirmation time - submission time.
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { ethers } = require("ethers");
const { CAMPUS_KEYS } = require("./keys");

const ROOT = path.join(__dirname, "..");
const CHAIN_ID = 2027;
const NODES = Number(process.env.NODES || 5); // 10 = validator + RPC node per campus cluster
const SUBMIT_BASE = Number(process.env.SUBMIT_BASE || 0); // 5 = campuses submit through their RPC node
const PEERS_MIN = Number(process.env.PEERS_MIN || Math.min(4, NODES - 1));
const RPC = Array.from({ length: NODES }, (_, i) => `http://127.0.0.1:${8545 + i}`);
const sub = (c) => SUBMIT_BASE + c; // node that campus c submits to
const ALL = [0, 1, 2, 3, 4];
// With RPC nodes, a campus whose validator is down still submits through its own RPC node.
const LIVE_S3 = SUBMIT_BASE ? ALL : [0, 1, 2, 3];
const LIVE_S4 = SUBMIT_BASE ? ALL : [0, 1, 2];
const RATE = Number(process.env.RATE || 20); // tx/s aggregate
const S1_SECONDS = Number(process.env.S1_SECONDS || 60);
const S3_SECONDS = Number(process.env.S3_SECONDS || 60);
const S4_SECONDS = Number(process.env.S4_SECONDS || 15);
const BURST = Number(process.env.BURST || 60);
const READS = Number(process.env.READS || 1000);
// S6 saturation ramp: offered rates (tx/s, aggregate over the five campuses), RAMP_SECONDS each; RAMP="" skips it.
const RAMP = (process.env.RAMP ?? "20,40,60,80,100,120,160").split(",").filter(Boolean).map(Number);
const RAMP_SECONDS = Number(process.env.RAMP_SECONDS || 40);
const RAMP_WARMUP_S = 10; // throughput is counted after the pipeline has filled
const ONLY_RAMP = process.env.ONLY_RAMP === "1"; // skip S1–S5 (saturation runs)
const GAS_LIMIT = 400000n;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => performance.timeOrigin + performance.now();
const providers = RPC.map((u) => new ethers.JsonRpcProvider(u, CHAIN_ID, { staticNetwork: true, batchMaxCount: 1 }));
const wallets = CAMPUS_KEYS.map((k) => new ethers.Wallet(k));
const artifact = JSON.parse(
  fs.readFileSync(path.join(ROOT, "artifacts/contracts/CertificateConsortium.sol/CertificateConsortium.json"), "utf8"),
);
const iface = new ethers.Interface(artifact.abi);
const net = (...args) => execFileSync("bash", [path.join(ROOT, "network/net.sh"), ...args], { stdio: "inherit" });

function pct(xs, p) {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const k = (s.length - 1) * p;
  const lo = Math.floor(k);
  const hi = Math.ceil(k);
  return s[lo] + (s[hi] - s[lo]) * (k - lo);
}
function meanSd(xs) {
  if (!xs.length) return { mean: null, sd: null, n: 0 };
  const m = xs.reduce((a, b) => a + b, 0) / xs.length;
  const sd = xs.length > 1 ? Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / (xs.length - 1)) : 0;
  return { mean: m, sd, n: xs.length };
}
async function blockNumber(i) {
  try {
    return Number(await providers[i].send("eth_blockNumber", []));
  } catch {
    return -1;
  }
}

// ---------------------------------------------------------------- block watcher (validator 0)
const seen = new Map(); // txHash -> confirmation time (ms)
const blocks = []; // {number, timestamp, txCount, gasUsed, observedAt}
let lastBlock = 0;
let watching = true;
async function watch() {
  lastBlock = await blockNumber(0);
  while (watching) {
    try {
      const b = await blockNumber(0);
      for (let n = lastBlock + 1; b > 0 && n <= b; n++) {
        const blk = await providers[0].send("eth_getBlockByNumber", [ethers.toQuantity(n), false]);
        if (!blk) break; // head advertised before the block is queryable (slow nodes): retry next poll
        const t = now();
        blocks.push({ number: n, timestamp: Number(blk.timestamp), txCount: blk.transactions.length, gasUsed: Number(blk.gasUsed), observedAt: t });
        for (const hsh of blk.transactions) if (!seen.has(hsh)) seen.set(hsh, t);
        lastBlock = n;
      }
    } catch {
      /* transient RPC error on a throttled node: retry next poll */
    }
    await sleep(100);
  }
}

// ---------------------------------------------------------------- transaction sending
let contractAddress;
const nonces = [];
const chains = [Promise.resolve(), Promise.resolve(), Promise.resolve(), Promise.resolve(), Promise.resolve()];
let hashCounter = 0;
const issued = []; // docHashes successfully confirmed (for S5)

async function refreshNonces(campuses) {
  for (const c of campuses) nonces[c] = await providers[sub(c)].getTransactionCount(wallets[c].address, "pending");
}

async function signIssue(c) {
  const docHash = ethers.keccak256(ethers.toUtf8Bytes(`signed-pdf-${Date.now()}-${c}-${hashCounter++}`));
  const tx = {
    type: 0,
    chainId: CHAIN_ID,
    nonce: nonces[c]++,
    to: contractAddress,
    data: iface.encodeFunctionData("issue", [docHash, 1]),
    gasLimit: GAS_LIMIT,
    gasPrice: 0n,
    value: 0n,
  };
  const raw = await wallets[c].signTransaction(tx);
  return { raw, hash: ethers.keccak256(raw), docHash, campus: c };
}

function errMsg(e) {
  const inner = e?.error?.message || e?.info?.error?.message || "";
  return String(inner || e.shortMessage || e.message).slice(0, 200);
}

// A failed submission must not leave a nonce gap (later transactions of the same campus would wait
// forever as "future" transactions), so the same signed transaction is retried with backoff.
// Answers meaning "this transaction is already there" count as a successful submission.
async function sendWithRetry(rec) {
  for (let attempt = 0; attempt < 6; attempt++) {
    try {
      await providers[sub(rec.campus)].send("eth_sendRawTransaction", [rec.raw]);
      rec.sent = true;
      return;
    } catch (e) {
      const msg = errMsg(e);
      if (/already known|known transaction|nonce too low|already been used/i.test(msg) && attempt > 0) {
        rec.sent = true;
        return;
      }
      rec.error = msg;
      rec.retries = attempt + 1;
      await sleep(200 * 2 ** attempt);
    }
  }
  rec.sent = false;
}

function submit(rec, records) {
  chains[rec.campus] = chains[rec.campus].then(async () => {
    rec.submittedAt = now();
    await sendWithRetry(rec);
  });
  records.push(rec);
}

async function drain(records, maxMs) {
  const t0 = now();
  while (now() - t0 < maxMs) {
    if (records.filter((r) => r.sent).every((r) => seen.has(r.hash))) break;
    await sleep(200);
  }
}

async function receiptsGas(records, max = 100) {
  const conf = records.filter((r) => seen.has(r.hash)).slice(0, max);
  const gas = [];
  let reverted = 0;
  for (const r of conf) {
    const rc = await providers[0].send("eth_getTransactionReceipt", [r.hash]);
    if (!rc) continue;
    if (Number(rc.status) !== 1) reverted++;
    gas.push(Number(rc.gasUsed));
  }
  return { ...meanSd(gas), reverted, sampled: conf.length };
}

function metrics(name, records, extra = {}) {
  const sent = records.filter((r) => r.sent);
  const conf = sent.filter((r) => seen.has(r.hash));
  const lat = conf.map((r) => (seen.get(r.hash) - r.submittedAt) / 1000);
  const firstSubmit = Math.min(...sent.map((r) => r.submittedAt));
  const lastConfirm = conf.length ? Math.max(...conf.map((r) => seen.get(r.hash))) : null;
  const tps = conf.length && lastConfirm ? conf.length / ((lastConfirm - firstSubmit) / 1000) : 0;
  const win = blocks.filter((b) => b.observedAt >= firstSubmit && (!lastConfirm || b.observedAt <= lastConfirm + 1));
  const intervals = win.slice(1).map((b, i) => b.timestamp - win[i].timestamp);
  for (const r of conf) issued.push(r.docHash);
  const m = {
    scenario: name,
    submitted: records.length,
    accepted: sent.length,
    rejectedAtSubmit: records.length - sent.length,
    confirmed: conf.length,
    confirmedPct: records.length ? (100 * conf.length) / records.length : 0,
    tps,
    latency: { p50: pct(lat, 0.5), p95: pct(lat, 0.95), mean: meanSd(lat).mean, max: lat.length ? Math.max(...lat) : null },
    blocks: {
      count: win.length,
      meanTxPerBlock: meanSd(win.map((b) => b.txCount)).mean,
      maxTxPerBlock: win.length ? Math.max(...win.map((b) => b.txCount)) : 0,
      meanIntervalS: meanSd(intervals).mean,
      maxIntervalS: intervals.length ? Math.max(...intervals) : null,
    },
    retriedSubmissions: records.filter((r) => r.retries).length,
    errors: [...new Set(records.filter((r) => r.error).map((r) => r.error))].slice(0, 5),
    ...extra,
  };
  const f = (x, d = 2) => (x == null ? "—" : x.toFixed(d));
  console.log(
    `${name.padEnd(28)} TPS ${f(m.tps)}  p50 ${f(m.latency.p50)} s  p95 ${f(m.latency.p95)} s  confirmed ${m.confirmed}/${m.submitted} (${f(m.confirmedPct, 1)} %)`,
  );
  return m;
}

async function paced(seconds, rate, campuses, records) {
  const total = Math.round(seconds * rate);
  const interval = 1000 / rate;
  const start = now();
  for (let k = 0; k < total; k++) {
    const wait = start + k * interval - now();
    if (wait > 0) await sleep(wait);
    const c = campuses[k % campuses.length];
    submit(await signIssue(c), records);
  }
  await Promise.all(chains);
}

// Like paced(), but a campus does not wait for the answer to one submission before sending the next (at most
// maxInflight unanswered per campus), so the generator itself can offer well over 100 tx/s to emulated nodes.
async function pacedConcurrent(seconds, rate, campuses, records, maxInflight = Number(process.env.MAX_INFLIGHT || 16)) {
  const total = Math.round(seconds * rate);
  const interval = 1000 / rate;
  const inflight = new Map(campuses.map((c) => [c, 0]));
  const pending = [];
  const start = now();
  for (let k = 0; k < total; k++) {
    const wait = start + k * interval - now();
    if (wait > 0) await sleep(wait);
    const c = campuses[k % campuses.length];
    const rec = await signIssue(c);
    while (inflight.get(c) >= maxInflight) await sleep(2);
    inflight.set(c, inflight.get(c) + 1);
    rec.submittedAt = now();
    records.push(rec);
    pending.push(sendWithRetry(rec).finally(() => inflight.set(c, inflight.get(c) - 1)));
  }
  await Promise.all(pending);
}

async function waitSynced(i, maxMs = 300000) {
  const t0 = now();
  while (now() - t0 < maxMs) {
    const [a, b] = [await blockNumber(0), await blockNumber(i)];
    if (b > 0 && a - b <= 1) return (now() - t0) / 1000;
    await sleep(500);
  }
  return null;
}

// Measurements start only once the network is stable: every node answers, has at least PEERS_MIN peers, all
// heads are within one block, and that has held while the chain advanced STABLE_BLOCKS blocks. (Block
// intervals are not required to be exactly 2 s: on Pi-class CPUs occasional QBFT round changes are part of
// the behaviour being measured.)
async function waitStable(stableBlocks = Number(process.env.STABLE_BLOCKS || 10), maxMs = 600000) {
  const t0 = now();
  let firstOk = null;
  let last = null;
  while (now() - t0 < maxMs) {
    try {
      const heads = [];
      const peerList = [];
      let ok = true;
      for (let i = 0; i < NODES; i++) {
        // Head agreement (checked below) is the sync criterion: Besu's eth_syncing can stay non-false on
        // healthy full nodes while its sync manager waits for a "sync target", so it is not used.
        const [b, peers] = await Promise.all([
          providers[i].send("eth_blockNumber", []),
          providers[i].send("net_peerCount", []),
        ]);
        heads.push(Number(b));
        peerList.push(Number(peers));
        if (Number(peers) < PEERS_MIN) ok = false;
      }
      last = { heads, peers: peerList };
      const top = Math.max(...heads);
      if (ok && top - Math.min(...heads) <= 1) {
        if (firstOk == null) firstOk = top;
        if (top - firstOk >= stableBlocks) return { waitedS: (now() - t0) / 1000, atBlock: top };
      } else {
        firstOk = null;
      }
    } catch (e) {
      last = { error: String(e.shortMessage || e.message).slice(0, 120) };
    }
    await sleep(2000);
  }
  throw new Error(`network did not stabilise: ${JSON.stringify(last)}`);
}

async function main() {
  const results = { startedAt: new Date().toISOString(), rate: RATE, nodes: NODES, submitThroughRpcNodes: SUBMIT_BASE > 0, interCampusLatencyMs: Number(process.env.LATENCY_MS || 0), scenarios: {} };
  // Slow (emulated) nodes may still be opening their RPC port when the network starts: wait up to 3 min for each.
  for (let i = 0; i < NODES; i++) {
    const t0 = now();
    while ((await blockNumber(i)) < 1) {
      if (now() - t0 > 180000) throw new Error(`node ${i} not responding`);
      await sleep(1000);
    }
  }
  results.stabilisation = await waitStable();
  console.log(`Network stable at block ${results.stabilisation.atBlock} after ${results.stabilisation.waitedS.toFixed(0)} s`);
  watch();

  // Deploy D2 with campus 1 as deployer; the five campus accounts are the founding members.
  const deployer = wallets[0].connect(providers[0]);
  const factory = new ethers.ContractFactory(artifact.abi, artifact.bytecode, deployer);
  const c = await factory.deploy(
    wallets.map((w) => w.address),
    [1, 2, 3, 4, 5],
    [1, 2, 3, 4, 5].map((i) => ethers.keccak256(ethers.toUtf8Bytes(`x509-campus-${i}`))), // placeholder certificate fingerprints
    { gasPrice: 0n, type: 0 },
  );
  const deployRc = await c.deploymentTransaction().wait();
  contractAddress = await c.getAddress();
  results.contract = contractAddress;
  results.deploymentGas = Number(deployRc.gasUsed);
  console.log(`CertificateConsortium deployed at ${contractAddress} (${deployRc.gasUsed} gas)`);

  // Warm-up: one certificate per campus so balance slots are initialised (steady state).
  await refreshNonces([0, 1, 2, 3, 4]);
  const warm = [];
  for (let k = 0; k < 5; k++) submit(await signIssue(k), warm);
  await Promise.all(chains);
  await drain(warm, 30000);

  let s1 = [], s2 = [], s3 = [], s4 = [];
  if (!ONLY_RAMP) {
  // S1 steady load.
  await refreshNonces([0, 1, 2, 3, 4]);
  s1 = [];
  await paced(S1_SECONDS, RATE, [0, 1, 2, 3, 4], s1);
  await drain(s1, 60000);
  results.scenarios.S1 = metrics(`S1 steady ${RATE} tx/s`, s1, { durationS: S1_SECONDS, issueGas: await receiptsGas(s1) });

  // S2 burst of BURST concurrent transactions (spread over the five campuses).
  await refreshNonces([0, 1, 2, 3, 4]);
  const signed = [];
  for (let k = 0; k < BURST; k++) signed.push(await signIssue(k % 5));
  s2 = [];
  for (const rec of signed) submit(rec, s2);
  await Promise.all(chains);
  await drain(s2, 60000);
  results.scenarios.S2 = metrics(`S2 burst of ${BURST}`, s2);

  // S3 one validator down (node 4); the other four campuses share the same aggregate rate.
  net("stop-node", "4");
  await sleep(10000);
  await refreshNonces(LIVE_S3);
  s3 = [];
  await paced(S3_SECONDS, RATE, LIVE_S3, s3);
  await drain(s3, 90000);
  results.scenarios.S3 = metrics("S3 one validator down", s3, { durationS: S3_SECONDS, stopped: [4] });
  net("start-node", "4");
  results.scenarios.S3.rejoinSyncS = await waitSynced(4);
  console.log(`  node 4 back in sync after ${results.scenarios.S3.rejoinSyncS} s`);
  await waitStable(5);

  // S4 two validators down (nodes 3 and 4): QBFT loses its 2/3 quorum and halts.
  net("stop-node", "3");
  net("stop-node", "4");
  await sleep(6000);
  const haltedAt = await blockNumber(0);
  await refreshNonces(LIVE_S4);
  s4 = [];
  const outageStart = now();
  await paced(S4_SECONDS, RATE, LIVE_S4, s4);
  await sleep(10000);
  const confirmedDuringOutage = s4.filter((r) => seen.has(r.hash)).length;
  const blocksDuringOutage = (await blockNumber(0)) - haltedAt;
  const outageS = (now() - outageStart) / 1000;
  const restartAt = now();
  net("start-node", "3");
  let node3UpS = null;
  let resumeS = null;
  while (now() - restartAt < 600000) {
    if (node3UpS == null && (await blockNumber(3)) >= 0) node3UpS = (now() - restartAt) / 1000;
    if ((await blockNumber(0)) > haltedAt + blocksDuringOutage) {
      resumeS = (now() - restartAt) / 1000;
      break;
    }
    await sleep(200);
  }
  await drain(s4, 180000);
  const s4m = metrics("S4 two validators down", s4, { stopped: [3, 4] });
  results.scenarios.S4 = {
    ...s4m,
    duringOutage: {
      confirmed: confirmedDuringOutage,
      confirmedPct: (100 * confirmedDuringOutage) / s4.length,
      blocksProduced: blocksDuringOutage,
      outageS,
      tps: 0,
    },
    recovery: {
      node3RpcUpS: node3UpS,
      resumeAfterRestartS: resumeS,
      confirmedAfterRecovery: s4m.confirmed - confirmedDuringOutage,
      confirmedAfterRecoveryPct: s4m.confirmedPct,
    },
  };
  console.log(
    `  outage ${outageS.toFixed(1)} s: ${confirmedDuringOutage} confirmed, ${blocksDuringOutage} blocks; ` +
      `blocks resumed ${resumeS == null ? "—" : resumeS.toFixed(1)} s after restarting validator 3 (RPC up at ${node3UpS} s)`,
  );
  net("start-node", "4");
  await waitSynced(3);
  await waitSynced(4);

  // S5 read-only verification (eth_call verify) against validator 2.
  const ver = new ethers.Contract(contractAddress, artifact.abi, providers[sub(2)]);
  const lat = [];
  let validCount = 0;
  // A failed read (e.g. "Internal error" from a node under emulation) is recorded and retried once instead of
  // aborting the run; its latency is not counted.
  const callErrors = [];
  for (let k = 0; k < READS; k++) {
    const hsh = issued[k % issued.length];
    for (let attempt = 0; attempt < 2; attempt++) {
      const t0 = now();
      try {
        const r = await ver.verify(hsh);
        lat.push((now() - t0) / 1000);
        if (r[0]) validCount++;
        break;
      } catch (e) {
        callErrors.push(errMsg(e));
        await sleep(200);
      }
    }
  }
  results.scenarios.S5 = {
    scenario: "S5 verification (read)",
    calls: READS,
    returnedValid: validCount,
    callErrors: callErrors.length,
    callErrorSamples: [...new Set(callErrors)].slice(0, 5),
    latency: { p50: pct(lat, 0.5), p95: pct(lat, 0.95), mean: meanSd(lat).mean, max: Math.max(...lat) },
  };
  console.log(
    `S5 verification (read)       p50 ${(pct(lat, 0.5) * 1000).toFixed(2)} ms  p95 ${(pct(lat, 0.95) * 1000).toFixed(2)} ms  valid ${validCount}/${READS}, failed calls ${callErrors.length}`,
  );

  } // end of S1–S5

  // S6 saturation ramp (after S5, so it cannot disturb S1–S5; or alone with ONLY_RAMP=1). Each step offers a
  // higher aggregate rate for RAMP_SECONDS with concurrent submission, then waits up to 60 s for its transactions.
  // Steady-state throughput counts confirmations after the first RAMP_WARMUP_S seconds of the step. A step is
  // harness-limited if the generator could not submit at 90 % of the offered rate; it is saturated if the network
  // confirmed less than 90 % of the submitted rate in steady state or left transactions unconfirmed after the wait.
  // The ramp stops at the first saturated or harness-limited step.
  if (RAMP.length) {
    try {
      const steps = [];
      for (const rate of RAMP) {
        await waitStable(3);
        await refreshNonces(ALL);
        const recs = [];
        await pacedConcurrent(RAMP_SECONDS, rate, ALL, recs);
        const sentRecs = recs.filter((r) => r.sent);
        const subs = sentRecs.map((r) => r.submittedAt);
        const t0 = subs.length ? Math.min(...subs) : now();
        const submitRate = subs.length > 1 ? (subs.length - 1) / ((Math.max(...subs) - t0) / 1000) : 0;
        await drain(recs, 60000);
        const inWindow = sentRecs.filter((r) => {
          const t = seen.get(r.hash);
          return t && t >= t0 + RAMP_WARMUP_S * 1000 && t <= t0 + RAMP_SECONDS * 1000;
        }).length;
        const steadyTps = inWindow / (RAMP_SECONDS - RAMP_WARMUP_S);
        const m = metrics(`S6 ramp ${rate} tx/s`, recs, { offered: rate, durationS: RAMP_SECONDS, submitRate, steadyTps });
        m.harnessLimited = submitRate < 0.9 * rate;
        m.saturated = !m.harnessLimited && (steadyTps < 0.9 * submitRate || m.confirmed < m.submitted);
        console.log(`   step ${rate} tx/s: submitted at ${submitRate.toFixed(1)} tx/s, steady-state ${steadyTps.toFixed(1)} tx/s` +
          `${m.harnessLimited ? " (generator limit)" : ""}${m.saturated ? " (saturated)" : ""}`);
        steps.push(m);
        if (m.saturated || m.harnessLimited) break;
      }
      const ok = steps.filter((m) => !m.saturated && !m.harnessLimited);
      results.scenarios.S6 = {
        scenario: "S6 saturation ramp",
        steps,
        maxSustainedOffered: ok.length ? Math.max(...ok.map((m) => m.offered)) : null,
        firstSaturatedOffered: (steps.find((m) => m.saturated) || {}).offered ?? null,
        harnessLimitedAt: (steps.find((m) => m.harnessLimited) || {}).offered ?? null,
        peakSteadyTps: Math.max(...steps.map((m) => m.steadyTps)),
        gasCeilingTps: 30000000 / 133508 / 2,
      };
      const S6 = results.scenarios.S6;
      console.log(`S6 saturation: sustained up to ${S6.maxSustainedOffered} tx/s offered; first saturated step ${S6.firstSaturatedOffered}` +
        ` tx/s; generator limit at ${S6.harnessLimitedAt}; peak steady-state ${S6.peakSteadyTps.toFixed(1)} tx/s` +
        ` (gas ceiling ${S6.gasCeilingTps.toFixed(0)} tx/s)`);
    } catch (e) {
      results.scenarios.S6 = { scenario: "S6 saturation ramp", error: errMsg(e) };
      console.log(`S6 saturation ramp failed: ${errMsg(e)}`);
    }
  }

  watching = false;
  // Transactions of each scenario included in any block by the end of the run (not only within its drain window).
  for (const [k, recs] of Object.entries({ S1: s1, S2: s2, S3: s3, S4: s4 })) {
    if (results.scenarios[k]) results.scenarios[k].includedByEndOfRun = recs.filter((r) => seen.has(r.hash)).length;
  }
  results.finishedAt = new Date().toISOString();
  results.blockLog = blocks.map(({ number, timestamp, txCount, gasUsed }) => ({ number, timestamp, txCount, gasUsed }));
  fs.mkdirSync(path.join(ROOT, "results"), { recursive: true });
  fs.writeFileSync(path.join(ROOT, "results/network.json"), JSON.stringify(results, null, 2));
  console.log("Saved results/network.json");
  process.exit(0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
