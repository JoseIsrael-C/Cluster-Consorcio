# Experiment kit · federated certificate consortium

Reproduces every result of Section V of the paper.

```bash
bash run-all.sh            # ~20 min; results in results/RESULTS.md
```

| Step | Command | Output |
|---|---|---|
| Tests T1–T12 (Table V) | `npx hardhat test` | `results/tests.txt` |
| Coverage (Table V) | `npx hardhat coverage` | `results/coverage-summary.json` |
| Static analysis (Table V) | `slither .` | `results/slither.json` |
| Gas, 30 runs per function (Table VI) | `npx hardhat run scripts/gas-benchmark.js` | `results/gas-hardhat.{json,csv}` |
| 5-validator QBFT network | `bash network/net.sh setup && bash network/net.sh start` | `network/run/` |
| Scenarios S1–S5 (Table VII) | `node scripts/loadgen.js` | `results/network.json` |
| Environment (Table IV) | `node scripts/env.js` | `results/environment.json` |
| Median of several network runs (Table VII) | `node scripts/aggregate-runs.js results/runs/<a> results/runs/<b> …` | `results/network-summary.json` |

On macOS, double-click `ejecutar-red.command` (one run), `ejecutar-red-x3.command` (three runs) or `ejecutar-red-pi-x3.command` (three runs on emulated Raspberry Pi 4B clusters, about 50 min); each run is archived in `results/runs/`.

### Raspberry Pi 4B emulation (`bash run-all.sh network-pi`)

Five campus clusters of five Pi 4B (4 GB) boards are emulated on one host. Per cluster, one board runs the campus's QBFT validator and one a non-validating RPC node (campuses submit through it); the backend, database and signer boards are not on the measured path (the load generator stands in for them). Each Besu JVM gets `-XX:ActiveProcessorCount=4 -Xmx1536m` and is duty-cycled with SIGSTOP/SIGCONT by `scripts/throttle.js` so that each thread runs at the speed of a Pi 4B core: target 287/4263 = 0.0673 of the host's speed (Geekbench 6 single-core, Pi 4B Rev 1.5 at 1.8 GHz vs Apple M5). `node scripts/throttle.js calibrate` measures the achieved slowdown on a CPU-bound workload and corrects the duty cycle (result in `results/pi-calibration.json`). Not emulated: storage speed and network latency between campuses. Read latencies (S5) include the 60 ms scheduling granularity and are upper bounds. The paper reports the median of three runs; `results/runs/README.md` lists every run, including the discarded ones and why.

## Contracts

- `CertificateConsortium.sol` (D2, proposed): ERC-721 + ERC-5192, Listing 1, with `revoke`, `reissue`, `recordTransfer`.
- `ConsortiumGovernance.sol`: membership shared by D2 and D3; admit/readmit 3 of 5, suspend 4 of 5.
- `HashRegistry.sol` (D3): D2 without the token layer.
- `prototype/CertificadosContract.sol` (D1): the earlier prototype's contract, **verbatim** (from the prototype's Django project). `scripts/prototype-data.js` builds records exactly as the prototype's views pass them; `scripts/run_prototype_integration.py` runs the prototype's own `contrato.py`, unmodified, against a local node (`npx hardhat node --port 7545`) and records gas and failures.

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
