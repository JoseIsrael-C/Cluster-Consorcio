# Network runs

## Raspberry Pi 4B emulation, final contract, no added latency, with the saturation ramp (values used in the paper, v5)

Launcher: `ejecutar-red-pi-completar.command` (one full run, S1–S6) and its earlier three-run variant. Static peer lists (no discovery); CPU calibration must land within ±20 % of the Pi 4B target (0.0673 of native speed).

| Folder | Used in the paper | Notes |
|---|---|---|
| pi-20261028-000708, pi-20261028-011746, pi-20261028-014920 | yes: S1–S5 (median of the three) | Calibrated speed 0.059 / 0.057 / 0.072. S1 17.80 / 19.57 / 19.45 tx/s. The S6 ramp of -000708 used the first ramp version (wrong throughput formula) and is not used. |
| pi-rampa-20261028-010251, pi-20261028-011746, pi-20261028-014920 | yes: S6 (median of the three) | Sustained 60 / 80 / 80 tx/s offered; fell behind at 80 / 100 / 100 tx/s (in -014920 the RPC nodes accepted only 74.6 tx/s at the 100 tx/s step); peak steady-state 66.6 / 78.8 / 70.9 tx/s. |
| descartadas/pi-20261028-002653, descartadas/pi-rampa-20261028-012340, descartadas/pi-rampa-20261028-013031 | no | Calibration ended at 0.032 / 0.014 / 0.015 of native speed (2–4.5 times slower than a Pi 4B); fixed in throttle.js and run-all.sh. |
| descartadas/pi-20261028-002933 | no | RPC node 7 was not answering when the load generator started; loadgen now waits up to 3 min. |
| descartadas/pi-20261028-004403, descartadas/pi-rampa-20261028-005712 | no | Network did not stabilise: with bootnode-only discovery a node kept one peer; static peer lists are now the default. |

Aggregate: `OUT=results/network-summary.json node scripts/aggregate-runs.js results/runs/pi-20261028-000708 results/runs/pi-20261028-011746 results/runs/pi-20261028-014920` and `OUT=results/network-summary-ramp.json node scripts/aggregate-runs.js results/runs/pi-rampa-20261028-010251 results/runs/pi-20261028-011746 results/runs/pi-20261028-014920`.

## Raspberry Pi 4B emulation, contract before the governance changes (values used in the paper up to v4)

5 clusters × 5 Pi 4B (4 GB): per cluster one QBFT validator and one RPC node run Besu; each JVM limited to 4 cores and a 1.5 GB heap and duty-cycled to Pi 4B per-core speed (scripts/throttle.js). Launcher: `ejecutar-red-pi-x3.command` (`./run-all.sh network-pi` three times).

| Folder | Used in the paper | Notes |
|---|---|---|
| pi-20261017-204208, pi-20261017-205515, pi-20261017-210750 | yes (median of the three) | Calibrated speed ratio 0.0648 / 0.0624 / 0.0665 (target 0.0673). |
| pi-20261017-200231 | no | Load generator crashed while watching blocks (null block on a lagging node). Fixed in loadgen.js. |
| pi-20261017-201521, pi-20261017-202815 | no | Stopped at "network did not stabilise": the stability check required eth_syncing=false and 2 s intervals, which throttled nodes rarely satisfy. Relaxed to peers ≥ 4 and heads within one block for ten blocks. |

Aggregate: `node scripts/aggregate-runs.js results/runs/pi-20261017-204208 results/runs/pi-20261017-205515 results/runs/pi-20261017-210750`

## Raspberry Pi 4B emulation with 20 ms between campuses (values used in the paper, v5)

Same setup plus `LATENCY_MS=20` (`scripts/latency-proxy.js`: a TCP relay per ordered pair of nodes, 20 ms each way between campuses, 0 ms within a campus; Besu with discovery disabled and static nodes pointing at the relays). Launchers: `ejecutar-red-pi-latencia-x3.command` (three runs) and `ejecutar-red-pi-latencia-x1.command` (one run); both keep the Mac awake with `caffeinate`.

| Folder | Used in the paper | Notes |
|---|---|---|
| pi-lat20-20261027-190519, pi-lat20-20261027-191629, pi-lat20-20261027-233728 | yes (median of the three) | Final contract. Duty cycle 0.236 / 0.211 / 0.174; S1 19.21 / 18.56 / 9.66 tx/s. Every transaction of S1–S4 included by the end of each run. |
| descartadas/pi-lat20-20261027-213333 | no | The Mac went to sleep during the run: calibration measured 0.003 of native speed and node 1 stopped answering; no network.json. |
| preliminar-lat20-contrato-previo/pi-lat20-20261027-182433, -184055, -185404 | no (mentioned in the text) | Contract before the stale-proposal fix (issuance identical). Duty cycle 0.16–0.22; S1 11.42 / 9.26 / 14.94 tx/s. In -184055 Besu refused 4 submissions ("nonce too distant from current sender nonce") and the gap held back 20 later transactions of that campus. -185404 stopped in S5 when a node answered a read with "Internal error" (S5 now records and retries failed reads). |

The slow runs are those where calibration assigned a smaller CPU share (duty cycle), so the spread in S1 reflects the emulation as much as the latency.

Aggregate: `OUT=results/network-summary-lat20.json node scripts/aggregate-runs.js results/runs/pi-lat20-20261027-190519 results/runs/pi-lat20-20261027-191629 results/runs/pi-lat20-20261027-233728`

## Native runs (no Pi emulation; used in the previous version of the paper)

| Folder | Used in the paper | Notes |
|---|---|---|
| 20261017-192153, 20261017-192802, 20261017-193418 | v2 only (median of the three) | Final load generator: retries on failed submissions and waits for a stable network before measuring. |
| run1 | no | Measured before the network had stabilised; S1 p95 4.5 s, S4 recovery 132 s. |
| run2-sin-reintentos | no | 17 submissions failed with a transient RPC error and were not retried, leaving nonce gaps (S1 82 % confirmed). Load-generator bug, fixed. |
| run3-sin-espera-estabilidad | no | Retries fixed, but S1 started while one validator was still syncing (p95 32.8 s). Fixed by waiting for stability. |

Aggregate (native): `node scripts/aggregate-runs.js results/runs/20261017-192153 results/runs/20261017-192802 results/runs/20261017-193418`
