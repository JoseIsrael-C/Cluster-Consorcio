#!/bin/bash
# Doble clic en Finder: emula 5 clústeres (uno por plantel) de 5 Raspberry Pi 4B de 4 GB y corre tres veces
# los escenarios S1–S5 con una red nueva cada vez. Cada corrida queda en results/runs/pi-<fecha-hora>/.
SRC="$(cd "$(dirname "$0")" && pwd)"
RUN="$HOME/.kit-consorcio-run"
for i in 1 2 3; do
  echo "================ Corrida $i de 3 (Raspberry Pi 4B emulada) ================"
  mkdir -p "$RUN" "$SRC/results/logs"
  (cd "$SRC" && tar --exclude=./node_modules --exclude=./.tools --exclude=./results --exclude=./retirado -cf - .) | (cd "$RUN" && tar -xf -)
  rm -f "$RUN/contracts/PrototypeRegistry.sol"
  rm -f "$RUN/results/network.json" "$RUN/results/pi-calibration.json" "$RUN/results/throttle-stats.json"
  mkdir -p "$RUN/results/logs"
  (cd "$RUN" && bash run-all.sh network-pi 2>&1) | tee "$SRC/results/logs/run-network-pi.log"
  STAMP=pi-$(date +%Y%m%d-%H%M%S)
  mkdir -p "$SRC/results/runs/$STAMP"
  cp "$RUN/results/network.json" "$RUN/results/environment.json" "$RUN/results/pi-calibration.json" \
     "$RUN/results/throttle-stats.json" "$RUN/results/logs/loadgen.log" "$RUN/results/logs/throttle.log" \
     "$RUN/results/logs/pi-calibration.log" "$SRC/results/runs/$STAMP/" 2>/dev/null
  cp "$SRC/results/logs/run-network-pi.log" "$SRC/results/runs/$STAMP/" 2>/dev/null
  echo "Corrida $i archivada en results/runs/$STAMP"
  sleep 5
done
echo "Listo. Ya puedes cerrar esta ventana."
