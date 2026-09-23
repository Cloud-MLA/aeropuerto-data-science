-- Q1 — Recurso (manga/radar) con más incidencias en los últimos N días.
-- Motor: AWS Athena (Trino/Presto) sobre catálogo Glue `aeropuerto_lake`.
-- Endpoint MS5: GET /api/analitica/recursos-mas-fallas?dias={N}
-- Reemplazar {dias} manualmente con el valor entero antes de correr en consola.

WITH incidencias_ventana AS (
    SELECT
        i.id             AS incidencia_id,
        i.gravedad,
        -- fecha_reporte/fecha_cierre llegan como varchar ISO 8601 ("...T...Z") porque el
        -- crawler de Glue las infiere como string, no timestamp (mismo ajuste que en Q2/Q5 -- DS-10).
        from_iso8601_timestamp(i.fecha_reporte) AS fecha_reporte,
        CASE WHEN i.fecha_cierre IS NOT NULL AND i.fecha_cierre != ''
             THEN from_iso8601_timestamp(i.fecha_cierre) END AS fecha_cierre,
        iar.id_recurso
    FROM incidencia i
    JOIN incidencia_afecta_recurso iar ON iar.id_incidencia = i.id
    WHERE from_iso8601_timestamp(i.fecha_reporte) > current_timestamp - INTERVAL '7' DAY
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
                 THEN date_diff('minute', iv.fecha_reporte, iv.fecha_cierre)
            END
        ),
        1
    )                            AS tpr_minutos_promedio
FROM incidencias_ventana iv
JOIN recurso r ON r.id = iv.id_recurso
GROUP BY r.id, r.tipo, r.nombre_tecnico_locacion
ORDER BY severidad_ponderada DESC, incidencias_total DESC
LIMIT 10;
