#!/bin/bash
# Doble clic en Finder: corre los escenarios S1–S5 de la red Besu QBFT y guarda los resultados en results/.
# Se ejecuta en una copia fuera de iCloud (~/.kit-consorcio-run) para no sincronizar node_modules, Java ni Besu.
# Cada corrida queda archivada en results/runs/<fecha-hora>/.
SRC="$(cd "$(dirname "$0")" && pwd)"
RUN="$HOME/.kit-consorcio-run"
mkdir -p "$RUN" "$SRC/results/logs"
(cd "$SRC" && tar --exclude=./node_modules --exclude=./.tools --exclude=./results -cf - .) | (cd "$RUN" && tar -xf -)
mkdir -p "$RUN/results/logs"
echo "Kit del consorcio · escenarios de red (unos 15 minutos). No cierres esta ventana."
cd "$RUN" && bash run-all.sh network 2>&1 | tee "$SRC/results/logs/run-network.log"
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$SRC/results/runs/$STAMP"
cp "$RUN/results/network.json" "$RUN/results/environment.json" "$RUN/results/logs/loadgen.log" "$SRC/results/runs/$STAMP/" 2>/dev/null
cp "$SRC/results/logs/run-network.log" "$SRC/results/runs/$STAMP/" 2>/dev/null
cp "$RUN/results/network.json" "$RUN/results/environment.json" "$SRC/results/" 2>/dev/null
echo
echo "Terminado. Resultados en $SRC/results/runs/$STAMP."
