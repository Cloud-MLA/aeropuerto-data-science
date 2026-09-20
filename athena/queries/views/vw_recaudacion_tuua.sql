-- Vista `vw_recaudacion_tuua` — recaudación TUUA por categoría migratoria (Q4 materializada).
-- Motor: AWS Athena (Trino/Presto).
-- Consumida por MS5 en GET /api/analitica/recaudacion-tuua-por-categoria.
--
-- Cierra DS-12 del plan. Ejecutar en la consola Athena UNA vez tras DS-11.
-- Después:  SHOW VIEWS IN aeropuerto_lake;  // debe listar vw_recaudacion_tuua

CREATE OR REPLACE VIEW vw_recaudacion_tuua AS
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
CROSS JOIN totales t;
