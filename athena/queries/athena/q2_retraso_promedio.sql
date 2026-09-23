-- Q2 — Retraso promedio (min) por tipo de vuelo, con percentiles y franja horaria.
-- Motor: AWS Athena (Trino/Presto). Endpoint: GET /api/analitica/retraso-promedio?tipo=Internacional

WITH retrasos AS (
    SELECT
        v.id,
        v.numero AS num_vuelo,
        -- hora_programada/hora_real llegan como varchar ISO 8601 con offset (2026-09-30
        -- 06:15:00+00:00) porque el crawler de Glue las infiere como string; from_iso8601_timestamp
        -- las parsea sin tener que ajustar el tipo de columna en el catalogo (DS-10).
        from_iso8601_timestamp(replace(v.hora_programada, ' ', 'T')) AS hora_programada,
        v.aerolinea_ruc,
        CAST(date_diff('minute', from_iso8601_timestamp(replace(v.hora_programada, ' ', 'T')), from_iso8601_timestamp(replace(v.hora_real, ' ', 'T'))) AS DOUBLE) AS retraso_min,
        CASE CAST(EXTRACT(HOUR FROM from_iso8601_timestamp(replace(v.hora_programada, ' ', 'T'))) AS INTEGER) / 6
             WHEN 0 THEN 'Madrugada (0-6)'
             WHEN 1 THEN 'Manana (6-12)'
             WHEN 2 THEN 'Tarde (12-18)'
             ELSE       'Noche (18-24)'
        END AS franja_horaria
    FROM vuelo v
    WHERE v.tipo = 'Internacional'
      AND v.estado IN ('Retrasado', 'Despegado', 'Aterrizado')
      AND v.hora_real IS NOT NULL
      AND v.hora_real != ''
)
SELECT
    'GLOBAL' AS grupo,
    'Todo el periodo' AS categoria,
    COUNT(*) AS vuelos,
    ROUND(AVG(retraso_min), 2) AS retraso_promedio_min,
    ROUND(stddev(retraso_min), 2) AS desv_estandar_min,
    ROUND(approx_percentile(retraso_min, 0.50), 2) AS p50,
    ROUND(approx_percentile(retraso_min, 0.90), 2) AS p90,
    ROUND(approx_percentile(retraso_min, 0.99), 2) AS p99
FROM retrasos

UNION ALL

SELECT
    'POR FRANJA' AS grupo,
    franja_horaria,
    COUNT(*),
    ROUND(AVG(retraso_min), 2),
    ROUND(stddev(retraso_min), 2),
    ROUND(approx_percentile(retraso_min, 0.50), 2),
    ROUND(approx_percentile(retraso_min, 0.90), 2),
    ROUND(approx_percentile(retraso_min, 0.99), 2)
FROM retrasos
GROUP BY franja_horaria
ORDER BY grupo, categoria;
