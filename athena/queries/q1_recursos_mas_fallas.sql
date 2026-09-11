-- Q1 — Recurso con más incidencias en la última semana.
--
-- Motivación de negocio: identificar la manga o el radar que satura al equipo
-- de mantenimiento. No basta con contar — pesamos por gravedad, medimos el
-- porcentaje de incidencias que siguen abiertas (sin `fecha_cierre`) y el
-- tiempo promedio de reparación (TPR) de las cerradas.
--
-- Endpoint MS5: GET /analitica/recursos-mas-fallas?dias=7
-- Parámetro `dias` se sustituye en la clausula INTERVAL.
--
-- ATHENA: reemplazar `NOW()` por `current_timestamp` y `INTERVAL '7' DAY`
--         por `INTERVAL '7' DAY` (Trino ya lo soporta igual).
-- ATHENA: reemplazar `EXTRACT(EPOCH FROM ...)` por
--         `date_diff('minute', fecha_reporte, fecha_cierre)` — mas limpio.

WITH incidencias_ventana AS (
    SELECT
        i.id             AS incidencia_id,
        i.gravedad,
        i.fecha_reporte,
        i.fecha_cierre,
        iar.id_recurso
    FROM ms3.incidencia i
    JOIN ms3.incidencia_afecta_recurso iar ON iar.id_incidencia = i.id
    WHERE i.fecha_reporte > NOW() - INTERVAL '7' DAY
)
SELECT
    r.id                         AS recurso_id,
    r.tipo,
    r.nombre_tecnico_locacion,
    COUNT(*)                     AS incidencias_total,
    SUM(CASE WHEN iv.gravedad = 'Critica'  THEN 4
             WHEN iv.gravedad = 'Alta'     THEN 3
             WHEN iv.gravedad = 'Moderada' THEN 2
             ELSE 1 END)         AS severidad_ponderada,
    SUM(CASE WHEN iv.gravedad = 'Critica' THEN 1 ELSE 0 END) AS incidencias_criticas,
    SUM(CASE WHEN iv.fecha_cierre IS NULL THEN 1 ELSE 0 END) AS incidencias_abiertas,
    ROUND(
        100.0 * SUM(CASE WHEN iv.fecha_cierre IS NULL THEN 1 ELSE 0 END) / COUNT(*),
        2
    )                            AS pct_abiertas,
    ROUND(
        AVG(
            CASE WHEN iv.fecha_cierre IS NOT NULL
                 THEN EXTRACT(EPOCH FROM (iv.fecha_cierre - iv.fecha_reporte)) / 60.0
            END
        )::numeric,
        1
    )                            AS tpr_minutos_promedio
FROM incidencias_ventana iv
JOIN ms3.recurso r ON r.id = iv.id_recurso
GROUP BY r.id, r.tipo, r.nombre_tecnico_locacion
ORDER BY severidad_ponderada DESC, incidencias_total DESC
LIMIT 10;
