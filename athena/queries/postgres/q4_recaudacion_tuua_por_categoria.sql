-- Q4 — Recaudación TUUA por categoría migratoria.
--
-- Motivación de negocio: ingreso concesionario por Tarifa Única Uso Aeroportuario.
-- La recaudación real solo cuenta pasajeros que efectivamente embarcaron —
-- excluimos tickets Emitido/No-show/Cancelado y vuelos Cancelados.
--
-- Endpoint MS5: GET /analitica/recaudacion-tuua-por-categoria
--
-- Notas:
-- - La tarifa TUUA se toma de ms1.categoria_migratoria (no del precio del ticket,
--   que es el pasaje aereo — cosas distintas).
-- - `share_pct` es la participacion de cada categoria sobre la recaudacion total.
-- - Nacional: 12.50 · Internacional: 38.45 · Transito: 18.00 soles.
--
-- ATHENA: sintaxis estándar.

WITH pasajeros_efectivos AS (
    SELECT
        p.id_categoria,
        cm.nombre  AS categoria,
        cm.tarifa,
        COUNT(*)   AS pasajeros
    FROM ms1.ticket t
    JOIN ms1.pasajero p ON p.id_persona = t.id_persona
    JOIN ms1.categoria_migratoria cm ON cm.id = p.id_categoria
    JOIN ms2.vuelo v ON v.id = t.id_vuelo
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
