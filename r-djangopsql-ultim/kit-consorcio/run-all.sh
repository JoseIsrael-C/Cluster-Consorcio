#!/usr/bin/env bash
# Runs the whole evaluation and writes every result to ./results (summary: results/RESULTS.md).
#   bash run-all.sh            all steps
#   bash run-all.sh contracts  tests + coverage + gas + Slither only (no Besu network)
#   bash run-all.sh network    Besu network scenarios only
# Works on macOS (Apple silicon or Intel) and Linux. Node.js, Java 21 and Besu are downloaded into
# ./.tools when they are not already installed; nothing is installed system-wide.
set -uo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
TOOLS="$ROOT/.tools"
LOGS="$ROOT/results/logs"
mkdir -p "$TOOLS" "$LOGS"
MODE="${1:-all}"

say() { printf '\n\033[1;34m== %s ==\033[0m\n' "$*"; }
die() { printf '\033[1;31mERROR: %s\033[0m\n' "$*"; exit 1; }

case "$(uname -s)" in Darwin) OS=mac; NODE_OS=darwin ;; Linux) OS=linux; NODE_OS=linux ;; *) die "unsupported OS" ;; esac
case "$(uname -m)" in arm64|aarch64) ARCH=aarch64; NODE_ARCH=arm64 ;; x86_64) ARCH=x64; NODE_ARCH=x64 ;; *) die "unsupported CPU" ;; esac

# ------------------------------------------------------------------ Node.js >= 18
node_ok() { command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ] 2>/dev/null; }
if [ -d "$TOOLS/node/bin" ]; then export PATH="$TOOLS/node/bin:$PATH"; fi
if ! node_ok; then
  say "Downloading Node.js 22 into .tools"
  base="https://nodejs.org/dist/latest-v22.x"
  file=$(curl -fsSL "$base/SHASUMS256.txt" | awk '{print $2}' | grep -E "^node-v[0-9.]+-${NODE_OS}-${NODE_ARCH}\.tar\.gz$" | head -1)
  [ -n "$file" ] || die "could not find a Node.js build for ${NODE_OS}-${NODE_ARCH}"
  curl -fsSL "$base/$file" -o "$TOOLS/node.tgz" || die "Node.js download failed"
  rm -rf "$TOOLS/node" && mkdir -p "$TOOLS/node" && tar -xzf "$TOOLS/node.tgz" -C "$TOOLS/node" --strip-components 1
  export PATH="$TOOLS/node/bin:$PATH"
fi
echo "node $(node -v), npm $(npm -v)"

if [ ! -d node_modules/hardhat ]; then
  say "Installing Hardhat, OpenZeppelin and test tooling (npm)"
  npm install --no-audit --no-fund > "$LOGS/npm-install.log" 2>&1 || { tail -30 "$LOGS/npm-install.log"; die "npm install failed"; }
fi
say "Compiling contracts (solc 0.8.24)"
npx hardhat compile 2>&1 | tee "$LOGS/compile.log" || die "compilation failed"

run_contracts() {
  say "Functional and security tests (T1–T12)"
  npx hardhat test 2>&1 | tee results/tests.txt

  say "Coverage (solidity-coverage)"
  npx hardhat coverage > "$LOGS/coverage.log" 2>&1
  tail -25 "$LOGS/coverage.log"
  cp coverage/coverage-summary.json results/coverage-summary.json 2>/dev/null || echo "coverage summary not produced"
  npx hardhat compile > /dev/null 2>&1

  say "Gas benchmark (30 runs per function)"
  npx hardhat run scripts/gas-benchmark.js 2>&1 | tee "$LOGS/gas.log"

  say "Static analysis (Slither)"
  if command -v python3 >/dev/null; then
    if [ ! -x "$TOOLS/venv/bin/slither" ]; then
      python3 -m venv "$TOOLS/venv" > "$LOGS/slither.log" 2>&1 &&
        "$TOOLS/venv/bin/pip" install -q --upgrade pip >> "$LOGS/slither.log" 2>&1 &&
        "$TOOLS/venv/bin/pip" install -q slither-analyzer >> "$LOGS/slither.log" 2>&1
    fi
    if [ -x "$TOOLS/venv/bin/slither" ]; then
      export PATH="$TOOLS/venv/bin:$PATH"
      rm -f results/slither.json
      slither . --filter-paths "node_modules" --exclude-dependencies --json results/slither.json >> "$LOGS/slither.log" 2>&1
      tail -15 "$LOGS/slither.log"
    else
      echo "Slither could not be installed (see results/logs/slither.log); continuing"
    fi
  else
    echo "python3 not found; Slither skipped"
  fi
}

# Recent Besu releases (26.x) require Java 25; older ones run on Java 21.
java_ok() { command -v java >/dev/null && java -version 2>&1 | grep -Eq 'version "(2[5-9]|[3-9][0-9])'; }
setup_besu() {
  if [ -d "$TOOLS/jdk" ]; then
    JH=$(find "$TOOLS/jdk" -maxdepth 3 -type d -name Home | head -1); [ -n "$JH" ] || JH=$(find "$TOOLS/jdk" -mindepth 1 -maxdepth 1 -type d | head -1)
    export JAVA_HOME="$JH" PATH="$JH/bin:$PATH"
  fi
  if ! java_ok; then
    say "Downloading Java 25 (Eclipse Temurin) into .tools"
    curl -fsSL "https://api.adoptium.net/v3/binary/latest/25/ga/${OS}/${ARCH}/jdk/hotspot/normal/eclipse" -o "$TOOLS/jdk.tgz" || die "Java download failed"
    rm -rf "$TOOLS/jdk" && mkdir -p "$TOOLS/jdk" && tar -xzf "$TOOLS/jdk.tgz" -C "$TOOLS/jdk"
    JH=$(find "$TOOLS/jdk" -maxdepth 3 -type d -name Home | head -1); [ -n "$JH" ] || JH=$(find "$TOOLS/jdk" -mindepth 1 -maxdepth 1 -type d | head -1)
    export JAVA_HOME="$JH" PATH="$JH/bin:$PATH"
  fi
  java -version 2>&1 | head -1
  if [ -d "$TOOLS/besu/bin" ]; then export PATH="$TOOLS/besu/bin:$PATH"; fi
  if ! command -v besu >/dev/null; then
    say "Downloading Hyperledger Besu into .tools"
    url=""
    for repo in besu-eth/besu hyperledger/besu; do
      url=$(curl -fsSL "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null | node -e '
        let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{const j=JSON.parse(s);
        const a=(j.assets||[]).find(a=>/^besu-[0-9.]+\.tar\.gz$/.test(a.name));
        console.log(a?a.browser_download_url:(j.tag_name?`https://github.com/'"$repo"'/releases/download/${j.tag_name}/besu-${j.tag_name}.tar.gz`:""))}catch{console.log("")}})')
      [ -n "$url" ] && break
    done
    [ -n "$url" ] || die "could not find the latest Besu release on GitHub"
    echo "$url"
    curl -fsSL "$url" -o "$TOOLS/besu.tgz" || die "Besu download failed"
    rm -rf "$TOOLS/besu" && mkdir -p "$TOOLS/besu" && tar -xzf "$TOOLS/besu.tgz" -C "$TOOLS/besu" --strip-components 1
    export PATH="$TOOLS/besu/bin:$PATH"
  fi
  besu --version 2>/dev/null | grep -i besu | head -1
}

run_network() {
  setup_besu
  say "Starting the 5-validator QBFT network"
  bash network/net.sh stop > /dev/null 2>&1
  bash network/net.sh setup || die "genesis generation failed (see network/generated/operator.log)"
  bash network/net.sh start || die "network did not start (see network/run/node0.log)"
  say "Scenarios S1–S5 (about 10 minutes)"
  node scripts/loadgen.js 2>&1 | tee "$LOGS/loadgen.log"
  bash network/net.sh stop
}

# Five campus clusters of five Raspberry Pi 4B (4 GB) each, emulated on one host: per cluster one QBFT
# validator and one RPC node run Besu with four CPUs, a 1.5 GB heap and per-thread speed throttled to a
# Pi 4B core (scripts/throttle.js); campuses submit through their RPC node.
run_network_pi() {
  setup_besu
  say "Calibrating the Raspberry Pi 4B CPU emulation"
  node scripts/throttle.js calibrate | tee "$LOGS/pi-calibration.log"
  say "Starting 5 Pi-4B clusters: 5 validators + 5 RPC nodes"
  bash network/net.sh stop > /dev/null 2>&1
  bash network/net.sh setup || die "genesis generation failed (see network/generated/operator.log)"
  NODES=10 BESU_OPTS="-Xmx1536m -XX:ActiveProcessorCount=4" bash network/net.sh start || die "network did not start"
  node scripts/throttle.js run > "$LOGS/throttle.log" 2>&1 &
  local THR=$!
  say "Scenarios S1–S5 on the emulated clusters (about 15 minutes)"
  NODES=10 SUBMIT_BASE=5 BESU_OPTS="-Xmx1536m -XX:ActiveProcessorCount=4" node scripts/loadgen.js 2>&1 | tee "$LOGS/loadgen.log"
  kill "$THR" 2>/dev/null; wait "$THR" 2>/dev/null
  cp network/run/throttle-stats.json results/ 2>/dev/null
  NODES=10 bash network/net.sh stop
}

case "$MODE" in
  contracts) run_contracts ;;
  network) run_network ;;
  network-pi) run_network_pi ;;
  all) run_contracts; run_network ;;
  *) die "usage: bash run-all.sh [all|contracts|network|network-pi]" ;;
esac

# Make the locally downloaded tools visible to the environment report.
for d in "$TOOLS/venv/bin" "$TOOLS/besu/bin"; do if [ -d "$d" ]; then export PATH="$d:$PATH"; fi; done
JH=$(find "$TOOLS/jdk" -maxdepth 3 -type d -name Home 2>/dev/null | head -1)
[ -n "$JH" ] || JH=$(find "$TOOLS/jdk" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)
if [ -n "$JH" ]; then export JAVA_HOME="$JH" PATH="$JH/bin:$PATH"; fi
node scripts/env.js > /dev/null
say "Summary (results/RESULTS.md)"
node scripts/summarize.js
