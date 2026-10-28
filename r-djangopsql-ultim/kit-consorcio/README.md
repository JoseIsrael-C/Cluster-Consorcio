# Experiment kit · federated certificate consortium

Reproduces every result of Section 5 of the paper.

```bash
bash run-all.sh            # ~20 min; results in results/RESULTS.md
```

| Step | Command | Output |
|---|---|---|
| Unit tests T1–T17 and model-based governance tests (Table 5) | `npx hardhat test` | `results/tests.txt` |
| Longer model-based campaign | `PBT_RUNS=300 PBT_STEPS=80 PBT_SEED=777 npx hardhat test test/GovernanceModel.test.js` | console |
| Reference verifier, end-to-end (Section 5.1) | `python verifier/test_verifier.py` | `results/verifier-test.json` |
| Coverage (Table V) | `npx hardhat coverage` | `results/coverage-summary.json` |
| Static analysis (Table V) | `slither .` | `results/slither.json` |
| Gas, 30 runs per function (Table VI) | `npx hardhat run scripts/gas-benchmark.js` | `results/gas-hardhat.{json,csv}` |
| 5-validator QBFT network | `bash network/net.sh setup && bash network/net.sh start` | `network/run/` |
| Scenarios S1–S5 and saturation ramp S6 (Table 8, Section 5.3) | `node scripts/loadgen.js` (`ONLY_RAMP=1`: S6 only) | `results/network.json` |
| Same, 20 ms one way between campuses | `LATENCY_MS=20 bash run-all.sh network-pi` | `results/network.json` |
| Median of the latency runs (Table 8, rows + 20 ms) | `OUT=results/network-summary-lat20.json node scripts/aggregate-runs.js results/runs/pi-lat20-…` | `results/network-summary-lat20.json` |
| Environment (Table IV) | `node scripts/env.js` | `results/environment.json` |
| Median of several network runs (Table VII) | `node scripts/aggregate-runs.js results/runs/<a> results/runs/<b> …` | `results/network-summary.json` |

On macOS, double-click `ejecutar-red.command` (one run), `ejecutar-red-x3.command` (three runs) `ejecutar-red-pi-x3.command` (three runs on emulated Raspberry Pi 4B clusters, about 50 min) or `ejecutar-red-pi-latencia-x3.command` (the same with 20 ms between campuses); each run is archived in `results/runs/`.

### Raspberry Pi 4B emulation (`bash run-all.sh network-pi`)

Five campus clusters of five Pi 4B (4 GB) boards are emulated on one host. Per cluster, one board runs the campus's QBFT validator and one a non-validating RPC node (campuses submit through it); the backend, database and signer boards are not on the measured path (the load generator stands in for them). Each Besu JVM gets `-XX:ActiveProcessorCount=4 -Xmx1536m` and is duty-cycled with SIGSTOP/SIGCONT by `scripts/throttle.js` so that each thread runs at the speed of a Pi 4B core: target 287/4263 = 0.0673 of the host's speed (Geekbench 6 single-core, Pi 4B Rev 1.5 at 1.8 GHz vs Apple M5). `node scripts/throttle.js calibrate` measures the achieved slowdown on a CPU-bound workload and corrects the duty cycle (result in `results/pi-calibration.json`). Not emulated: storage speed. Inter-campus latency is optional: with `LATENCY_MS=20`, `scripts/latency-proxy.js` puts a TCP relay between every pair of nodes (no root needed); relays between campuses delay each direction by 20 ms, relays within a campus add nothing, and Besu runs with discovery disabled and a static-nodes file that points at the relays. Read latencies (S5) include the 60 ms scheduling granularity and are upper bounds. The paper reports the median of three runs; `results/runs/README.md` lists every run, including the discarded ones and why.

## Contracts

- `CertificateConsortium.sol` (D2, proposed): ERC-721 + ERC-5192, Listing 1, with `revoke`, `reissue`, `recordTransfer`.
- `ConsortiumGovernance.sol`: membership shared by D2 and D3; admission 4/5 of the active members, suspension 4/5 of the other members, readmission and certificate renewal (own campus only) by simple majority, emergency declaration by a majority of the other members (provisional for 14 days, at most 7 days back). Votes on stale proposals revert.
- `HashRegistry.sol` (D3): D2 without the token layer.
- `prototype/CertificadosContract.sol` (D1): the earlier prototype's contract, **verbatim** (from the prototype's Django project). `scripts/prototype-data.js` builds records exactly as the prototype's views pass them; `scripts/run_prototype_integration.py` runs the prototype's own `contrato.py`, unmodified, against a local node (`npx hardhat node --port 7545`) and records gas and failures.

## Verifier and read-only gateway

- `verifier/verify_certificate.py` performs the three checks of Section 3.2: (1) `verify(h)` with h = keccak256 of the
  revision signed by the first signature; (2) pyHanko validation of the PAdES signature against the trust anchor (the
  SAT certification authority in production), an RFC 3161 timestamp not later than the on-chain issuance time, and
  revocation (CRL/OCSP, hard-fail unless `--soft-fail`); (3) SHA-256 of the signer certificate = `signingCertAt(i, t)`.
  `pip install -r verifier/requirements.txt`, then
  `python verifier/verify_certificate.py titulo.pdf --rpc <gateway> --contract <address> --trust-anchor ac-sat.pem`.
- `verifier/test_verifier.py` builds a test PKI (a root standing in for the SAT authority, a TSA, one certificate per
  campus, a rogue CA), deploys D2 on `npx hardhat node`, signs PDFs with pyHanko and checks cases V1–V9 and G1–G3.
- `scripts/readonly-gateway.js`: the gateway operated by the consortium's oversight body. It forwards only
  `eth_chainId`, `net_version`, `eth_blockNumber` and `eth_call` to `verify`, `signingCertAt`, `compromiseCount`,
  `compromiseAt` on the consortium contract at the latest block; it logs time, function, outcome and the client address
  truncated to /24 (/48 for IPv6), never the parameters, and deletes daily log files older than `RETENTION_DAYS` (90).

## Method notes

- Compiler: solc 0.8.24, optimizer 200 runs, EVM `paris`. Hardhat Network runs London rules with zero base fee, matching the Besu genesis.
- Gas: receipt `gasUsed` (includes the 21,000 base cost and calldata). One warm-up call per function is excluded. Inputs are fixed, so repeated runs give identical values.
- Network: five Besu nodes on one host (RPC 8545–8549), QBFT, 2 s blocks, request timeout 4 s, zero base fee, gas price 0. Campus *i* signs locally and submits to validator *i*. Latency is measured from submission to the first block that contains the transaction (blocks polled every 100 ms from validator 0, which is never stopped).
- The load generator waits until every validator is in sync with four peers and ten consecutive blocks have been produced at the 2 s period, and it retries a failed submission with the same signed transaction so that no nonce gap can stall a campus.
- S3 stops validator 4 and keeps 20 tx/s across the four remaining campuses. S4 stops validators 3 and 4, submits for 15 s, then restarts validator 3 and measures the time until blocks resume.
- Campus keys are the public Hardhat development keys: test network only.

## Change log

- 2026-10-19 · Governance fix (`contracts/ConsortiumGovernance.sol`): the suspension threshold is now four fifths of the
  active members *other than the target*, who cannot vote on its own suspension. Before, it was computed over all active
  members, so after a first suspension (4 active) a second one needed 4 votes from only 3 eligible members and could never
  pass. Test T9 now covers both suspensions. Issuance, revocation and transfer gas are unchanged; deployment gas changed
  (D2 2,517,817; D3 1,441,629) and is re-measured in `results/gas-hardhat.json`. The Raspberry Pi network runs in
  `results/runs/pi-*` used the previous version; they do not exercise suspension.
- 2026-10-26 · Review fixes. Governance: admission now needs four fifths of the active members (closes a capture path
  through simple-majority admissions); a suspension may declare the campus compromised from a given time, and its
  certificates issued from then on stop verifying (emergency revocation); each campus is bound to the SHA-256 fingerprint
  of its X.509 signing certificate (`signingCertAt(campus, time)`, renewal by simple majority, history kept). New tests
  T13 (identity binding), T14 (emergency revocation), T15 (input validation): 15/15 pass, 100 % lines, 87.0 % branches,
  Slither 0 findings in D2 + governance. Constructor now takes `(accounts, campusIds, certFingerprints)`. Issuance gas is
  unchanged (D2 133,508); deployment D2 3,129,938, D3 2,058,515. The network runs in results/runs/pi-* used the
  previous version and do not exercise governance.
- 2026-10-26 (second review) · Certificate renewal can be proposed only by the campus itself (no coalition can replace
  another campus's certificate). Emergency revocation has its own threshold: a simple majority of the members other than
  the target declares the campus compromised from a time up to 7 days in the past; the declaration lapses after 14 days
  unless a suspension confirms it, and a renewal after readmission closes the compromise period. Tests T13, T14, T16:
  16/16 pass (18 with the baselines), 100 % lines, 88.1 % branches. Slither: two intended low-severity timestamp notices.
  Deployment D2 3,431,405, D3 2,362,608; issuance unchanged (D2 133,508).
- 2026-10-27 · Third review (points 5–9). (5) `verifier/verify_certificate.py`, a reference verifier for the three
  checks (pyHanko + Web3.py), with an end-to-end test on a test PKI (`verifier/test_verifier.py`, 12/12 cases).
  (6) Optional inter-campus latency (`LATENCY_MS`, `scripts/latency-proxy.js`, static nodes in `network/net.sh`) and
  `ejecutar-red-pi-latencia-x3.command` / `-x1.command` (both keep the Mac awake with `caffeinate`); the three runs
  reported in the paper used the final contract (median S1 18.56 tx/s, range 9.66–19.21, every transaction included;
  `results/network-summary-lat20.json`). A run made while the Mac fell asleep is in `results/runs/descartadas/`. Three earlier
  runs with the contract before the fix below are kept in `results/runs/preliminar-lat20-contrato-previo/` (the third
  stopped in S5 when a node answered a read with "Internal error"; S5 now records and retries failed reads, and every
  run reports how many transactions of each scenario were included by the end of the run). (8) `scripts/readonly-gateway.js` (allow-list of view calls,
  no parameters in logs, 90-day retention). (9) `test/GovernanceModel.test.js`, model-based tests of the governance
  state machine against a reference model (50 sequences × 60 steps by default; 300 × 80 with seed 777 in
  `results/model-based-campaign-300x80-seed777.txt`). They found three defects, now fixed in
  `ConsortiumGovernance.sol` and reproduced by T17: votes on stale proposals (a second suspension or readmission of the
  same campus) changed `activeMembers` twice; a suspension could declare a compromise start without the 7-day bound;
  a declaration voted late could reach back more than 7 days. Votes on stale proposals now revert (`StaleProposal`),
  and declarations are clamped to 7 days before execution. 69 tests pass (T1–T17, 2 baselines, 50 sequences);
  100 % lines, 91.3 % branches. Slither: three intended low-severity timestamp notices. Deployment D2 3,515,699,
  D3 2,446,416; issuance unchanged (D2 133,508).
- 2026-10-28 · Review point 4. S6 saturation ramp in `scripts/loadgen.js` (20, 40, 60, 80, 100, 120, 160 tx/s, 40 s
  steps, concurrent submission, steady-state throughput after 10 s; stops at the first step where the network
  confirms less than 90 % of the submitted rate). `ejecutar-red-pi-completar.command` runs S1–S6 once. Discovery is
  off by default (`STATIC_NODES=1` in `network/net.sh`): bootnode-only discovery left nodes with one peer in two runs.
  CPU calibration (`scripts/throttle.js`) now brackets the target over up to 8 rounds and `run-all.sh` retries it
  three times and discards the run unless the emulated speed is within ±20 % of a Pi 4B core; three runs that had
  been calibrated at 0.014–0.032 of native speed (target 0.067) are in `results/runs/descartadas/`. The no-latency
  rows of Table 8 now come from three runs with the final contract (`results/network-summary.json`) and the ramp from
  three runs (`results/network-summary-ramp.json`).

