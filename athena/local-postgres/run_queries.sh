#!/usr/bin/env bash
# Ejecuta Q1..Q5 y guarda la salida en ../expected/ para uso como "resultado
# esperado" al comparar contra futuras corridas o al portar a Athena.
#
# Uso: bash run_queries.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUERIES_DIR="$(cd "${SCRIPT_DIR}/../queries" && pwd)"
EXPECTED_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)/expected"

mkdir -p "${EXPECTED_DIR}"

for q in q1_recursos_mas_fallas q2_retraso_promedio q3_incidencias_combustible_por_aerolinea q4_recaudacion_tuua_por_categoria q5_vuelos_hora_punta_retrasados; do
    echo "==> Ejecutando ${q}.sql"
    docker exec -i aeropuerto-lake-local psql -U aeropuerto -d aeropuerto_lake \
        -f "-" < "${QUERIES_DIR}/${q}.sql" > "${EXPECTED_DIR}/${q}.txt"
    echo "    -> guardado en expected/${q}.txt ($(wc -l < "${EXPECTED_DIR}/${q}.txt") lineas)"
done

echo "==> Listo. Los resultados esperados estan en ${EXPECTED_DIR}"
