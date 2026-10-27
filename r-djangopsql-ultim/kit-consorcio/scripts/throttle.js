// Raspberry Pi 4B emulation for the Besu processes of the network (CPU side).
// Every node process is duty-cycled with SIGSTOP/SIGCONT so that, per thread, it runs at the speed of a
// Pi 4B core. The factor is the ratio of Geekbench 6 single-core scores:
//   Raspberry Pi 4 Model B Rev 1.5, 1.8 GHz: 287   (browser.geekbench.com/v6/cpu/18384201)
//   Apple M5 (14-inch MacBook Pro):          4,263 (MacRumors, 17 Oct 2025)
// so PI_FACTOR = 287 / 4263 = 0.0673. Each JVM is also started with -XX:ActiveProcessorCount=4 (four
// cores) and a heap that fits in 4 GB of RAM (see network/net.sh).
//
//   node scripts/throttle.js calibrate       measures the achieved slowdown on a CPU-bound workload
//   node scripts/throttle.js run             throttles every pid in network/run/node*.pid until killed
const fs = require("fs");
const path = require("path");
const { spawn, execFileSync } = require("child_process");

const FACTOR = Number(process.env.PI_FACTOR || 287 / 4263);
const PERIOD_MS = Number(process.env.PI_PERIOD_MS || 60);
const RUN_DIR = path.join(__dirname, "..", "network", "run");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => performance.now();

function signal(pids, sig) {
  for (const p of pids) {
    try {
      process.kill(p, sig);
    } catch {
      /* process ended */
    }
  }
}

let ON_FACTOR = FACTOR; // duty actually commanded; calibration corrects it for signal/scheduling overhead
const CAL_FILE = path.join(__dirname, "..", "results", "pi-calibration.json");
try {
  ON_FACTOR = JSON.parse(fs.readFileSync(CAL_FILE, "utf8")).onFactor || FACTOR;
} catch {
  /* not calibrated yet */
}

async function dutyCycle(getPids, shouldRun) {
  const on = PERIOD_MS * ON_FACTOR;
  const off = PERIOD_MS - on;
  let onTotal = 0;
  let cycles = 0;
  const t0 = now();
  while (shouldRun()) {
    const pids = getPids();
    const a = now();
    signal(pids, "SIGCONT");
    await sleep(on);
    signal(pids, "SIGSTOP");
    onTotal += now() - a;
    cycles++;
    await sleep(off);
  }
  signal(getPids(), "SIGCONT");
  const elapsed = now() - t0;
  return { cycles, achievedDuty: onTotal / elapsed };
}

function nodePids() {
  if (!fs.existsSync(RUN_DIR)) return [];
  return fs
    .readdirSync(RUN_DIR)
    .filter((f) => /^node\d+\.pid$/.test(f))
    .map((f) => Number(fs.readFileSync(path.join(RUN_DIR, f), "utf8")))
    .filter((p) => p > 0);
}

const BENCH = `const c=require("crypto");let h=Buffer.alloc(32);const t=performance.now();
for(let i=0;i<${Number(process.env.PI_BENCH_ITERS || 1500000)};i++)h=c.createHash("sha256").update(h).digest();
console.log(performance.now()-t)`;

function benchFree() {
  return Number(execFileSync(process.execPath, ["-e", BENCH]).toString());
}

async function benchThrottled() {
  const child = spawn(process.execPath, ["-e", BENCH]);
  let out = "";
  let done = false;
  child.stdout.on("data", (d) => (out += d));
  const ended = new Promise((r) => child.on("exit", () => ((done = true), r())));
  const t0 = now();
  const duty = dutyCycle(() => [child.pid], () => !done);
  await ended;
  const wall = now() - t0;
  return { wall, duty: await duty };
}

async function calibrate() {
  const free = [benchFree(), benchFree(), benchFree()].sort((a, b) => a - b)[1];
  ON_FACTOR = FACTOR;
  let thr;
  const rounds = [];
  for (let round = 0; round < 3; round++) {
    thr = await benchThrottled();
    const ratio = free / thr.wall;
    rounds.push({ onFactor: ON_FACTOR, achievedSpeedRatio: ratio });
    if (Math.abs(ratio - FACTOR) / FACTOR < 0.05) break;
    ON_FACTOR = Math.min(0.5, ON_FACTOR * (FACTOR / ratio));
  }
  const last = rounds.reduce((b, r) => (Math.abs(r.achievedSpeedRatio - FACTOR) < Math.abs(b.achievedSpeedRatio - FACTOR) ? r : b));
  const res = {
    piFactorTarget: FACTOR,
    periodMs: PERIOD_MS,
    onFactor: last.onFactor,
    freeMs: free,
    achievedSpeedRatio: last.achievedSpeedRatio,
    equivalentGeekbench6SingleCore: Math.round(last.achievedSpeedRatio * 4263),
    rounds,
  };
  console.log(JSON.stringify(res, null, 2));
  return res;
}

async function main() {
  const mode = process.argv[2] || "run";
  if (mode === "calibrate") {
    const res = await calibrate();
    fs.mkdirSync(path.join(__dirname, "..", "results"), { recursive: true });
    fs.writeFileSync(CAL_FILE, JSON.stringify(res, null, 2));
    return;
  }
  let running = true;
  const stop = () => (running = false);
  process.on("SIGTERM", stop);
  process.on("SIGINT", stop);
  console.log(`Throttling Besu nodes: target ${(FACTOR * 100).toFixed(2)} % of native speed, commanded duty ${(ON_FACTOR * 100).toFixed(2)} % (period ${PERIOD_MS} ms)`);
  const res = await dutyCycle(nodePids, () => running);
  fs.writeFileSync(path.join(RUN_DIR, "throttle-stats.json"), JSON.stringify(res, null, 2));
  console.log(`Throttle stopped: ${res.cycles} cycles, achieved duty ${(res.achievedDuty * 100).toFixed(2)} %`);
}

main();
