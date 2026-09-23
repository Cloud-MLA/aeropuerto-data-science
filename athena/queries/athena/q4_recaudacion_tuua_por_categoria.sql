-- Q4 — Recaudación TUUA por categoría migratoria (solo pasajeros efectivos).
-- Motor: AWS Athena (Trino/Presto). Endpoint: GET /api/analitica/recaudacion-tuua-por-categoria
-- En producción MS5 consulta la vista vw_recaudacion_tuua (ver views/).

WITH pasajeros_efectivos AS (
    SELECT
        p.id_categoria,
        cm.nombre  AS categoria,
        cm.tarifa,
        COUNT(*)   AS pasajeros
    FROM ticket t
    JOIN pasajero p ON p.id_persona = t.id_persona
    JOIN categoria_migratoria cm ON cm.id = p.id_categoria
    JOIN vuelo v ON v.id = t.id_vuelo
    WHERE t.estado_boarding IN ('Check-in', 'Embarcado')
      AND v.estado <> 'Cancelado'
    GROUP BY p.id_categoria, cm.nombre, cm.tarifa
),
totales AS (
    SELECT SUM(pasajeros * tarifa) AS recaudacion_total FROM pasajeros_efectivos
)
SELECT
    pe.categoria,
    pe.tarifa                                                   AS tarifa_tuua_soles,
    pe.pasajeros,
    ROUND(pe.pasajeros * pe.tarifa, 2)                          AS recaudacion_soles,
    ROUND(
        100.0 * (pe.pasajeros * pe.tarifa) / t.recaudacion_total,
        2
    )                                                           AS share_pct
FROM pasajeros_efectivos pe
CROSS JOIN totales t
ORDER BY recaudacion_soles DESC;
