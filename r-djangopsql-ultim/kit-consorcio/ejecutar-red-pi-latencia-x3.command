#!/bin/bash
# Doble clic en Finder: igual que ejecutar-red-pi-x3.command, pero con 20 ms de latencia en un sentido entre
# planteles (scripts/latency-proxy.js) y con la versión final de los contratos. Corre tres veces S1–S5 con una red
# nueva cada vez; cada corrida queda en results/runs/pi-lat20-<fecha-hora>/.
SRC="$(cd "$(dirname "$0")" && pwd)"
RUN="$HOME/.kit-consorcio-run"
caffeinate -dims -w $$ &
for i in 1 2 3; do
  echo "================ Corrida $i de 3 (Pi 4B emulada, 20 ms entre planteles) ================"
  mkdir -p "$RUN" "$SRC/results/logs"
  (cd "$SRC" && tar --exclude=./node_modules --exclude=./.tools --exclude=./results --exclude=./retirado -cf - .) | (cd "$RUN" && tar -xf -)
  rm -f "$RUN/contracts/PrototypeRegistry.sol"
  rm -f "$RUN/results/network.json" "$RUN/results/pi-calibration.json" "$RUN/results/throttle-stats.json"
  mkdir -p "$RUN/results/logs"
  (cd "$RUN" && LATENCY_MS=20 bash run-all.sh network-pi 2>&1) | tee "$SRC/results/logs/run-network-pi-lat.log"
  STAMP=pi-lat20-$(date +%Y%m%d-%H%M%S)
  mkdir -p "$SRC/results/runs/$STAMP"
  cp "$RUN/results/network.json" "$RUN/results/environment.json" "$RUN/results/pi-calibration.json" \
     "$RUN/results/throttle-stats.json" "$RUN/results/logs/loadgen.log" "$RUN/results/logs/throttle.log" \
     "$RUN/results/logs/pi-calibration.log" "$RUN/results/logs/latency-proxy.log" "$SRC/results/runs/$STAMP/" 2>/dev/null
  cp "$SRC/results/logs/run-network-pi-lat.log" "$SRC/results/runs/$STAMP/" 2>/dev/null
  echo "Corrida $i archivada en results/runs/$STAMP"
  sleep 5
done
echo "Listo. Ya puedes cerrar esta ventana."
