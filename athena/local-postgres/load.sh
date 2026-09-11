#!/usr/bin/env bash
# Aplana los JSONL de MS3 y hace \COPY de todos los CSVs a Postgres.
# Prerequisitos: docker compose up -d ya ejecutado.
#
# Uso: bash load.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detecta el binario de Python (Windows: py; Linux/Mac: python3 o python).
PYTHON_BIN=""
for candidate in py python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        # En Windows, `python` es un alias a Microsoft Store que sale con exit 9009;
        # descartamos si no responde a --version.
        if "$candidate" --version >/dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done
if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: no se encontro Python 3 (probado: py, python3, python)"
    exit 1
fi

echo "==> Aplanando JSONL de MS3 a CSV (con $PYTHON_BIN)..."
"$PYTHON_BIN" "${SCRIPT_DIR}/aplanar_ms3.py"

# Ejecuta un \COPY dentro del contenedor. El path es RELATIVO al contenedor
# porque ../../seeds/output esta montado como /csv (ver docker-compose.yml).
psql_copy() {
    local table="$1"
    local file_in_container="$2"
    docker exec -i aeropuerto-lake-local psql -U aeropuerto -d aeropuerto_lake \
        -c "\\COPY ${table} FROM '/csv/${file_in_container}' CSV HEADER"
}

echo "==> Cargando MS1..."
psql_copy "ms1.categoria_migratoria"  "ms1/categoria_migratoria.csv"
psql_copy "ms1.persona"               "ms1/persona.csv"
psql_copy "ms1.pasajero"              "ms1/pasajero.csv"
psql_copy "ms1.ticket"                "ms1/ticket.csv"
psql_copy "ms1.checkin"               "ms1/checkin.csv"
psql_copy "ms1.equipaje"              "ms1/equipaje.csv"

echo "==> Cargando MS2..."
psql_copy "ms2.aerolinea"             "ms2/aerolinea.csv"
psql_copy "ms2.aeronave"              "ms2/aeronave.csv"
psql_copy "ms2.asiento"               "ms2/asiento.csv"
psql_copy "ms2.empleado"              "ms2/empleado.csv"
psql_copy "ms2.tripulacion"           "ms2/tripulacion.csv"
psql_copy "ms2.operativo_tierra"      "ms2/operativo_tierra.csv"
psql_copy "ms2.vuelo"                 "ms2/vuelo.csv"
psql_copy "ms2.opera_tripulacion"     "ms2/opera_tripulacion.csv"

echo "==> Cargando MS3 (aplanado)..."
psql_copy "ms3.recurso"                   "ms3-flat/recurso.csv"
psql_copy "ms3.incidencia"                "ms3-flat/incidencia.csv"
psql_copy "ms3.incidencia_afecta_recurso" "ms3-flat/incidencia_afecta_recurso.csv"
psql_copy "ms3.incidencia_retrasa_vuelo"  "ms3-flat/incidencia_retrasa_vuelo.csv"
psql_copy "ms3.asignacion"                "ms3-flat/asignacion.csv"

echo "==> Conteos por tabla:"
docker exec -i aeropuerto-lake-local psql -U aeropuerto -d aeropuerto_lake -c "
SELECT 'ms1.persona' AS tabla, COUNT(*) AS filas FROM ms1.persona UNION ALL
SELECT 'ms1.pasajero',                COUNT(*) FROM ms1.pasajero UNION ALL
SELECT 'ms1.ticket',                  COUNT(*) FROM ms1.ticket UNION ALL
SELECT 'ms1.checkin',                 COUNT(*) FROM ms1.checkin UNION ALL
SELECT 'ms1.equipaje',                COUNT(*) FROM ms1.equipaje UNION ALL
SELECT 'ms2.aerolinea',               COUNT(*) FROM ms2.aerolinea UNION ALL
SELECT 'ms2.aeronave',                COUNT(*) FROM ms2.aeronave UNION ALL
SELECT 'ms2.asiento',                 COUNT(*) FROM ms2.asiento UNION ALL
SELECT 'ms2.vuelo',                   COUNT(*) FROM ms2.vuelo UNION ALL
SELECT 'ms2.opera_tripulacion',       COUNT(*) FROM ms2.opera_tripulacion UNION ALL
SELECT 'ms3.recurso',                 COUNT(*) FROM ms3.recurso UNION ALL
SELECT 'ms3.incidencia',              COUNT(*) FROM ms3.incidencia UNION ALL
SELECT 'ms3.incidencia_afecta_recurso', COUNT(*) FROM ms3.incidencia_afecta_recurso UNION ALL
SELECT 'ms3.incidencia_retrasa_vuelo', COUNT(*) FROM ms3.incidencia_retrasa_vuelo UNION ALL
SELECT 'ms3.asignacion',              COUNT(*) FROM ms3.asignacion
ORDER BY tabla;
"

echo "==> Carga completa."
