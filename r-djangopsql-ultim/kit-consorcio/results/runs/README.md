# Network runs

## Raspberry Pi 4B emulation (values used in the paper, v3)

5 clusters × 5 Pi 4B (4 GB): per cluster one QBFT validator and one RPC node run Besu; each JVM limited to 4 cores and a 1.5 GB heap and duty-cycled to Pi 4B per-core speed (scripts/throttle.js). Launcher: `ejecutar-red-pi-x3.command` (`./run-all.sh network-pi` three times).

| Folder | Used in the paper | Notes |
|---|---|---|
| pi-20261017-204208, pi-20261017-205515, pi-20261017-210750 | yes (median of the three) | Calibrated speed ratio 0.0648 / 0.0624 / 0.0665 (target 0.0673). |
| pi-20261017-200231 | no | Load generator crashed while watching blocks (null block on a lagging node). Fixed in loadgen.js. |
| pi-20261017-201521, pi-20261017-202815 | no | Stopped at "network did not stabilise": the stability check required eth_syncing=false and 2 s intervals, which throttled nodes rarely satisfy. Relaxed to peers ≥ 4 and heads within one block for ten blocks. |

Aggregate: `node scripts/aggregate-runs.js results/runs/pi-20261017-204208 results/runs/pi-20261017-205515 results/runs/pi-20261017-210750`

## Native runs (no Pi emulation; used in the previous version of the paper)

| Folder | Used in the paper | Notes |
|---|---|---|
| 20261017-192153, 20261017-192802, 20261017-193418 | v2 only (median of the three) | Final load generator: retries on failed submissions and waits for a stable network before measuring. |
| run1 | no | Measured before the network had stabilised; S1 p95 4.5 s, S4 recovery 132 s. |
| run2-sin-reintentos | no | 17 submissions failed with a transient RPC error and were not retried, leaving nonce gaps (S1 82 % confirmed). Load-generator bug, fixed. |
| run3-sin-espera-estabilidad | no | Retries fixed, but S1 started while one validator was still syncing (p95 32.8 s). Fixed by waiting for stability. |

Aggregate (native): `node scripts/aggregate-runs.js results/runs/20261017-192153 results/runs/20261017-192802 results/runs/20261017-193418`
