#!/bin/bash
# Doble clic en Finder: repite tres veces los escenarios S1–S5 (red nueva en cada corrida) y archiva
# cada una en results/runs/<fecha-hora>/. Unos 25 minutos en total.
SRC="$(cd "$(dirname "$0")" && pwd)"
for i in 1 2 3; do
  echo "================ Corrida $i de 3 ================"
  bash "$SRC/ejecutar-red.command"
  sleep 5
done
echo "Listo: tres corridas en $SRC/results/runs. Ya puedes cerrar esta ventana."
