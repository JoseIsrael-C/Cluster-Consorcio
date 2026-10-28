#!/bin/bash
# Doble clic en Finder: una corrida completa sin latencia con el contrato final (S1–S5 y la rampa de saturación
# S6, de 20 a 160 tx/s en escalones de 40 s). Queda en results/runs/pi-<fecha-hora>/. Si la emulación de CPU no
# queda dentro de ±20 % de la velocidad de una Pi 4B tras tres calibraciones, la corrida se descarta.
# caffeinate mantiene la Mac despierta.
SRC="$(cd "$(dirname "$0")" && pwd)"
RUN="$HOME/.kit-consorcio-run"
caffeinate -dims -w $$ &
for i in 1; do
  export ONLY_RAMP=0; KIND=pi
  echo "================ Corrida completa (Raspberry Pi 4B emulada) ================"
  mkdir -p "$RUN" "$SRC/results/logs"
  (cd "$SRC" && tar --exclude=./node_modules --exclude=./.tools --exclude=./results --exclude=./retirado -cf - .) | (cd "$RUN" && tar -xf -)
  rm -f "$RUN/contracts/PrototypeRegistry.sol"
  rm -f "$RUN/results/network.json" "$RUN/results/pi-calibration.json" "$RUN/results/throttle-stats.json"
  mkdir -p "$RUN/results/logs"
  (cd "$RUN" && bash run-all.sh network-pi 2>&1) | tee "$SRC/results/logs/run-network-pi-rampa.log"
  STAMP=$KIND-$(date +%Y%m%d-%H%M%S)
  mkdir -p "$SRC/results/runs/$STAMP"
  cp "$RUN/results/network.json" "$RUN/results/environment.json" "$RUN/results/pi-calibration.json" \
     "$RUN/results/throttle-stats.json" "$RUN/results/logs/loadgen.log" "$RUN/results/logs/throttle.log" \
     "$RUN/results/logs/pi-calibration.log" "$SRC/results/runs/$STAMP/" 2>/dev/null
  cp "$SRC/results/logs/run-network-pi-rampa.log" "$SRC/results/runs/$STAMP/" 2>/dev/null
  echo "Corrida $i archivada en results/runs/$STAMP"
  sleep 5
done
echo "Listo. Ya puedes cerrar esta ventana."
