// Read-only verification gateway (Section 3.6 of the paper). Operated by the consortium's joint oversight body,
// not by a campus, in front of a non-validating Besu node. It forwards only the read-only calls a verifier needs
// and keeps privacy-minimal logs:
//   - allowed: eth_chainId, net_version, eth_blockNumber, and eth_call to the consortium contract with the
//     selector of verify(bytes32), signingCertAt(uint8,uint64), compromiseCount(uint8) or compromiseAt(uint8,uint256);
//     everything else (transactions, logs, other contracts, debug/admin APIs) is refused;
//   - each log line holds only the time, the method/function name, the outcome and the client address truncated
//     to /24 (IPv4) or /48 (IPv6); the queried hash and other parameters are never written;
//   - one log file per day; files older than RETENTION_DAYS (default 90) are deleted at start and every hour.
//
//   UPSTREAM=http://127.0.0.1:8545 CONTRACT=0x... PORT=8600 LOG_DIR=results/gateway-logs RETENTION_DAYS=90 \
//     node scripts/readonly-gateway.js
const http = require("http");
const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");

const UPSTREAM = process.env.UPSTREAM || "http://127.0.0.1:8545";
const CONTRACT = (process.env.CONTRACT || "").toLowerCase();
const PORT = Number(process.env.PORT || 8600);
const LOG_DIR = process.env.LOG_DIR || path.join(__dirname, "..", "results", "gateway-logs");
const RETENTION_DAYS = Number(process.env.RETENTION_DAYS || 90);
const MAX_BODY = 16 * 1024;

const iface = new ethers.Interface([
  "function verify(bytes32)", "function signingCertAt(uint8,uint64)",
  "function compromiseCount(uint8)", "function compromiseAt(uint8,uint256)",
]);
const ALLOWED_CALLS = new Map(["verify", "signingCertAt", "compromiseCount", "compromiseAt"]
  .map((n) => [iface.getFunction(n).selector, n]));
const PLAIN = new Set(["eth_chainId", "net_version", "eth_blockNumber"]);

function truncateIp(ip) {
  const v4 = (ip || "").replace(/^::ffff:/, "");
  if (/^\d+\.\d+\.\d+\.\d+$/.test(v4)) return v4.split(".").slice(0, 3).join(".") + ".0/24";
  const parts = (ip || "").split(":");
  return parts.slice(0, 3).join(":") + "::/48";
}

function log(entry) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
  const day = new Date().toISOString().slice(0, 10);
  fs.appendFileSync(path.join(LOG_DIR, `gateway-${day}.log`), JSON.stringify(entry) + "\n");
}

function purge() {
  if (!fs.existsSync(LOG_DIR)) return;
  const cutoff = Date.now() - RETENTION_DAYS * 24 * 3600 * 1000;
  for (const f of fs.readdirSync(LOG_DIR)) {
    const m = /^gateway-(\d{4}-\d{2}-\d{2})\.log$/.exec(f);
    if (m && Date.parse(m[1] + "T00:00:00Z") < cutoff) fs.unlinkSync(path.join(LOG_DIR, f));
  }
}

// returns the label to log, or null if the request must be refused
function classify(req) {
  if (!req || req.jsonrpc !== "2.0" || typeof req.method !== "string") return null;
  if (PLAIN.has(req.method)) return req.method;
  if (req.method !== "eth_call" || !Array.isArray(req.params) || !req.params[0]) return null;
  const tx = req.params[0];
  const keys = Object.keys(tx).filter((k) => !["to", "data", "input"].includes(k));
  if (keys.length || !CONTRACT || String(tx.to || "").toLowerCase() !== CONTRACT) return null;
  const data = String(tx.data || tx.input || "");
  const fn = ALLOWED_CALLS.get(data.slice(0, 10).toLowerCase());
  const tag = req.params[1];
  if (!fn || (tag !== undefined && tag !== "latest")) return null; // no historical state queries
  return `eth_call:${fn}`;
}

async function forward(req) {
  const r = await fetch(UPSTREAM, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(req) });
  return r.json();
}

const server = http.createServer((hreq, hres) => {
  const client = truncateIp(hreq.socket.remoteAddress);
  if (hreq.method !== "POST") { hres.writeHead(405).end(); return; }
  let body = "";
  hreq.on("data", (c) => { body += c; if (body.length > MAX_BODY) hreq.destroy(); });
  hreq.on("end", async () => {
    let req;
    try { req = JSON.parse(body); } catch { req = null; }
    const batch = Array.isArray(req) ? req : [req];
    const out = [];
    for (const r of batch) {
      const label = classify(r);
      const time = new Date().toISOString();
      if (!label) {
        log({ time, method: r && typeof r.method === "string" ? r.method.slice(0, 40) : "invalid", outcome: "refused", client });
        out.push({ jsonrpc: "2.0", id: r && r.id !== undefined ? r.id : null, error: { code: -32601, message: "method not allowed by the read-only gateway" } });
        continue;
      }
      try {
        const res = await forward(r);
        log({ time, method: label, outcome: res.error ? "error" : "ok", client });
        out.push(res);
      } catch {
        log({ time, method: label, outcome: "upstream-unavailable", client });
        out.push({ jsonrpc: "2.0", id: r.id, error: { code: -32603, message: "upstream unavailable" } });
      }
    }
    hres.writeHead(200, { "content-type": "application/json" });
    hres.end(JSON.stringify(Array.isArray(req) ? out : out[0]));
  });
});

if (require.main === module) {
  if (!CONTRACT) { console.error("set CONTRACT to the consortium contract address"); process.exit(1); }
  purge();
  setInterval(purge, 3600 * 1000).unref();
  server.listen(PORT, () => console.log(`read-only gateway on :${PORT} -> ${UPSTREAM}, logs in ${LOG_DIR}, retention ${RETENTION_DAYS} days`));
}
module.exports = { classify, truncateIp, purge };
