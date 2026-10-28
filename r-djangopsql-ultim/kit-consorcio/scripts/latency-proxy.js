// Inter-campus latency for the emulated consortium (no root needed, works on macOS and Linux).
// Every Besu node reaches every other node through its own TCP relay. A relay between nodes of different
// campuses delays each chunk by LATENCY_MS in each direction (round trip 2 x LATENCY_MS); nodes of the same
// campus (validator i and RPC node 5+i) talk without added delay, as on a campus LAN. Order is preserved.
//   LATENCY_MS=20 NODES=10 node scripts/latency-proxy.js          (run in the background during a network run)
// Relay for a -> b listens on 127.0.0.1:(40000 + 16a + b) and forwards to b's P2P port 127.0.0.1:(30303 + b).
const net = require("net");

const NODES = Number(process.env.NODES || 10);
const DELAY = Number(process.env.LATENCY_MS || 20);
const campus = (k) => k % 5;
const relayPort = (a, b) => 40000 + 16 * a + b;

function delayedPipe(src, dst, delay) {
  let last = 0;
  src.on("data", (chunk) => {
    if (delay <= 0) return dst.write(chunk);
    const due = Math.max(Date.now() + delay, last);
    last = due;
    setTimeout(() => dst.writable && dst.write(chunk), due - Date.now());
  });
  src.on("end", () => setTimeout(() => dst.end(), delay));
  src.on("error", () => dst.destroy());
}

let relays = 0;
for (let a = 0; a < NODES; a++) {
  for (let b = 0; b < NODES; b++) {
    if (a === b) continue;
    const d = campus(a) === campus(b) ? 0 : DELAY;
    const server = net.createServer((client) => {
      const upstream = net.connect(30303 + b, "127.0.0.1");
      upstream.on("error", () => client.destroy());
      client.on("error", () => upstream.destroy());
      delayedPipe(client, upstream, d);
      delayedPipe(upstream, client, d);
    });
    server.listen(relayPort(a, b), "127.0.0.1");
    relays++;
  }
}
console.log(`latency-proxy: ${relays} relays, ${DELAY} ms one way between campuses, 0 ms within a campus`);
module.exports = { relayPort };
