# Results for integration

## Table V · tests, coverage, static analysis

- Tests T1–T16 passing: **16 of 16** (whole suite: 18 passing, 0 failing)
  - T1: pass
  - T2: pass
  - T3: pass
  - T4: pass
  - T5: pass
  - T6: pass
  - T7: pass
  - T8: pass
  - T9: pass
  - T10: pass
  - T11: pass
  - T12: pass
- Coverage (CertificateConsortium.sol + ConsortiumGovernance.sol): lines **100.0 %**, branches **88.1 %**, functions 100.0 %, statements 100.0 %
  - CertificateConsortium.sol: lines 100.0 %, branches 87.5 %
  - ConsortiumGovernance.sol: lines 100.0 %, branches 88.3 %
- Slither: 15 findings in all kit contracts {"Low":4,"Informational":11}; **2 in D2 + governance** {"Low":2}
  - [Low/Medium] timestamp: ConsortiumGovernance._checkCompromiseTime(uint256) (contracts/ConsortiumGovernance.sol#152-154) uses timestamp for comparisons
  - [Low/Medium] timestamp: ConsortiumGovernance._issuedWhileCompromised(uint8,uint64) (contracts/ConsortiumGovernance.sol#260-269) uses timestamp for comparisons

## Table VI · gas per function, mean ± SD over 30 runs (Hardhat Network, London rules, warm-up excluded)

| Function | D1 prototype | D2 proposed | D3 registry |
|---|---|---|---|
| issue | 208,880 ± 63.8 | 133,508 ± 2.2 | 100,815 ± 3.7 |
| recordTransfer | — | 37,991 ± 0.0 | 37,961 ± 0.0 |
| revoke | 26,103 ± 0.0 | 33,028 ± 0.0 | 32,946 ± 0.0 |
| reissue | — | 164,725 ± 2.2 | — |
| deployment | 985,932 ± 0.0 | 3,431,405 ± 0.0 | 2,362,608 ± 0.0 |

- issue: D2 vs D1 36.1 % (208,880 → 133,508); token-layer overhead D2 − D3 = 32,693 gas (+32.4 %)
- recordTransfer: D2 vs D1 — %; revoke: D2 vs D1 -26.5 %
- deployment: D2 − D3 = 1,068,797 gas (ERC-721/ERC-5192 code)
- Abstract: issuance uses **[X] = 133,508** gas instead of **[Y] = 208,880**

## Table VII · last single run, results/network.json (5 validators, 2 s blocks)

| Scenario | TPS | p50 (s) | p95 (s) | Confirmed |
|---|---|---|---|---|
| S1 steady, 20 tx/s | 19.21 | 4.09 | 14.76 | 100.0 % (1200/1200) |
| S2 burst of 60 | 16.38 | 2.19 | 3.10 | 100.0 % (60/60) |
| S3 one validator down | 18.96 | 4.37 | 8.87 | 100.0 % (1200/1200) |
| S4 two validators down | 0 | — | — | 0.0 % (0/300) during a 25 s outage; 0 blocks |
| S5 verification (read) | — | 0.0088 | 0.0672 | — |

- S4 recovery: block production resumed **175.5 s** after restarting the fourth validator (its RPC answered at 39.9 s); afterwards 300 of the 300 queued transactions were confirmed (100.0 % in total).
- S3: mean block interval 3.47 s (max 7 s) vs S1 3.10 s; validator 4 resynchronised 90.6 s after restart.
- S1 blocks: 57.1 tx/block on average (max 222); issue gas on Besu (receipts, n=100): 133,507 ± 4.3, reverted 0.
- D2 deployment on Besu: 2,511,114 gas
- Abstract: **[Z] = 19.2 tx/s** sustained; **[W] = 4.09 s** median confirmation latency (S1)

## Table VII · median [min–max] over 3 runs (values used in the paper)

| Scenario | TPS | p50 (s) | p95 (s) | Confirmed |
|---|---|---|---|---|
| S1 steady, 20 tx/s | 19.21 [18.72–19.38] | 3.67 [2.79–4.09] | 10.26 [4.47–14.76] | 100 % |
| S2 burst of 60 | 16.49 [16.38–17.81] | 3.07 [2.19–3.08] | 3.37 [3.10–3.64] | 100 % |
| S3 one validator down | 18.59 [17.99–18.96] | 4.37 [4.09–4.80] | 8.87 [8.52–9.74] | 100 % |
| S4 two validators down | 0 | — | — | 0 % during a 25 s outage |
| S5 verification (read) | — | 0.0537 [0.0088–0.0559] | 0.0746 [0.0672–0.1279] | — |

- S4: blocks resumed 175.5 [174.2–181.1] s after restarting the fourth validator; 100 % of the queued transactions confirmed afterwards.
- Issue gas from Besu receipts: 133506.6 [133506.3–133506.8]
- Runs: results/runs/pi-20261017-204208, results/runs/pi-20261017-205515, results/runs/pi-20261017-210750
- Abstract: **[Z] = 19.2 tx/s**, **[W] = 3.67 s**

## Raspberry Pi 4B emulation (calibration per run)

Target: Geekbench 6 single-core 287 (Pi 4B, 1.8 GHz) / 4,263 (Apple M5) = 0.0673 of native speed; JVM -Xmx1536m -XX:ActiveProcessorCount=4.

| Run | commanded duty | achieved speed ratio | GB6 single-core equivalent |
|---|---|---|---|
| results/runs/pi-20261017-204208 | 0.198 | 0.0648 | 276 |
| results/runs/pi-20261017-205515 | 0.213 | 0.0624 | 266 |
| results/runs/pi-20261017-210750 | 0.211 | 0.0665 | 284 |

## Earlier prototype (contrato.py unmodified, Web3.py 8.0.0)

- Deployment: 985,932 gas
- emitir_certificado, form record (pattern B): 208,880 ± 64 gas, 30/30 succeeded
- emitir_certificado, document record with CURP (pattern A): 3 of 30 failed out of gas under the fixed 300,000 limit (successful ones: 259,221 ± 14291 gas)
- revocar_certificado: fails — AttributeError (rawTransaction attribute removed in current Web3.py)
- emitir_hash_alumno: fails — Web3RPCError (out of gas under the fixed limit)

## Table IV · environment

| Host (CPU, RAM, OS) | Apple M5 · Mac17,2, 10 cores, 16 GB RAM, macOS 27.0.1 (26A434) |
| Node.js / Hardhat / ethers | v22.23.3 / 2.29.1 / 6.17.0 |
| solc / optimizer | 0.8.24 / enabled, 200 runs (EVM paris) |
| OpenZeppelin Contracts | 5.0.2 |
| Hyperledger Besu | besu/v26.10.0/osx-aarch_64/openjdk-java-25; openjdk version "25.0.4.1" 2026-08-18 LTS; QBFT, 2 s blocks, 5 validators + 5 RPC nodes |
| solidity-coverage / Slither | 0.8.17 / null |
