#!/usr/bin/env bash
# Five-validator Hyperledger Besu QBFT network on one host (2 s blocks, zero base fee).
#   bash network/net.sh setup            generate genesis + validator keys (once)
#   bash network/net.sh start|stop|status
#   bash network/net.sh stop-node <0-4>  /  start-node <0-4>
# Node i: RPC http://127.0.0.1:(8545+i), P2P 127.0.0.1:(30303+i). Nodes 0-4 are validators; with NODES=10,
# nodes 5-9 are non-validating RPC nodes (one per campus). Requires `besu` (Java 25 for Besu 26.x) in PATH.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
GEN="$DIR/generated"
RUN="$DIR/run"
N=5                     # QBFT validators (one per campus)
NODES="${NODES:-5}"     # total Besu nodes; 10 = one validator + one RPC node per campus cluster
CHAIN_ID=2027
export BESU_OPTS="${BESU_OPTS:--Xmx768m}"

rpc_block() {
  curl -s -m 2 -X POST -H 'Content-Type: application/json' \
    --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' "http://127.0.0.1:$((8545 + $1))" |
    node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{console.log(parseInt(JSON.parse(s).result,16))}catch{console.log(-1)}})'
}

setup() {
  rm -rf "$GEN" "$RUN"; mkdir -p "$GEN" "$RUN"
  local alloc
  alloc=$(cd "$ROOT" && node -e '
    const { ethers } = require("ethers"); const { CAMPUS_KEYS } = require("./scripts/keys");
    const a = {}; for (const k of CAMPUS_KEYS) a[new ethers.Wallet(k).address.slice(2).toLowerCase()] = { balance: "0x3635C9ADC5DEA00000" };
    console.log(JSON.stringify(a));')
  cat > "$GEN/qbftConfigFile.json" <<JSON
{
  "genesis": {
    "config": {
      "chainId": $CHAIN_ID,
      "berlinBlock": 0,
      "londonBlock": 0,
      "zeroBaseFee": true,
      "qbft": { "blockperiodseconds": 2, "epochlength": 30000, "requesttimeoutseconds": 4 }
    },
    "nonce": "0x0",
    "timestamp": "0x58ee40ba",
    "gasLimit": "0x1C9C380",
    "difficulty": "0x1",
    "mixHash": "0x63746963616c2062797a616e74696e65206661756c7420746f6c6572616e6365",
    "coinbase": "0x0000000000000000000000000000000000000000",
    "alloc": $alloc
  },
  "blockchain": { "nodes": { "generate": true, "count": $N } }
}
JSON
  besu operator generate-blockchain-config --config-file="$GEN/qbftConfigFile.json" \
    --to="$GEN/out" --private-key-file-name=key > "$GEN/operator.log" 2>&1
  cp "$GEN/out/genesis.json" "$GEN/genesis.json"
  local i=0 d
  for d in "$GEN"/out/keys/*/; do
    mkdir -p "$GEN/node$i"
    cp "$d/key" "$d/key.pub" "$GEN/node$i/"
    basename "$d" > "$GEN/node$i/address"
    i=$((i + 1))
  done
  echo "Genesis and $i validator keys in network/generated"
}

bootnode() {
  local pub; pub=$(sed 's/^0x//' "$GEN/node0/key.pub")
  echo "enode://$pub@127.0.0.1:30303"
}

start_node() {
  local i=$1
  if [ -f "$RUN/node$i.pid" ] && kill -0 "$(cat "$RUN/node$i.pid")" 2>/dev/null; then return 0; fi
  mkdir -p "$RUN"
  local boot=""
  if [ "$i" -ne 0 ]; then boot="--bootnodes=$(bootnode)"; fi
  local keyopt=""
  if [ -f "$GEN/node$i/key" ]; then keyopt="--node-private-key-file=$GEN/node$i/key"; fi
  nohup besu \
    --data-path="$RUN/data$i" \
    --genesis-file="$GEN/genesis.json" \
    $keyopt \
    --sync-mode=FULL \
    --p2p-host=127.0.0.1 --p2p-port=$((30303 + i)) $boot \
    --rpc-http-enabled --rpc-http-host=127.0.0.1 --rpc-http-port=$((8545 + i)) \
    --rpc-http-api=ETH,NET,QBFT,WEB3,TXPOOL --host-allowlist='*' --rpc-http-cors-origins='*' \
    --min-gas-price=0 --engine-rpc-enabled=false \
    >> "$RUN/node$i.log" 2>&1 &
  echo $! > "$RUN/node$i.pid"
}

stop_node() {
  local i=$1 pid
  [ -f "$RUN/node$i.pid" ] || return 0
  pid=$(cat "$RUN/node$i.pid")
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 40); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$RUN/node$i.pid"
}

wait_blocks() {
  local b
  for _ in $(seq 1 120); do
    b=$(rpc_block 0)
    if [ "$b" -ge 2 ] 2>/dev/null; then echo "QBFT producing blocks (block $b)"; return 0; fi
    sleep 2
  done
  echo "Network did not produce blocks; see network/run/node*.log" >&2
  return 1
}

case "${1:-}" in
  setup) setup ;;
  start)
    for i in $(seq 0 $((NODES - 1))); do
      start_node "$i"
      if [ "$i" -eq 0 ]; then sleep 8; fi
    done
    wait_blocks ;;
  stop) for i in $(seq 0 9); do stop_node "$i"; done ;;
  start-node) start_node "$2" ;;
  stop-node) stop_node "$2" ;;
  status) for i in $(seq 0 $((NODES - 1))); do echo "node$i block $(rpc_block "$i")"; done ;;
  *) sed -n '2,7p' "$0" ;;
esac
