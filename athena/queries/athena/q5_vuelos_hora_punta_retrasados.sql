-- Q5 — % de vuelos en hora punta retrasados (comparativa A/B).
-- Motor: AWS Athena (Trino/Presto). Endpoint: GET /api/analitica/vuelos-hora-punta-retrasados
-- En producción MS5 consulta la vista vw_retrasos_hora_punta (ver views/).

WITH base AS (
    SELECT
        v.id,
        v.tipo,
        v.estado,
        -- hora_programada/hora_real son varchar ISO 8601 con offset en el catalogo (el crawler
        -- de Glue las infiere como string); from_iso8601_timestamp las parsea sin tocar el tipo
        -- de columna (DS-10). hora_real llega como '' (no NULL) cuando el vuelo aun no aterriza.
        from_iso8601_timestamp(replace(v.hora_programada, ' ', 'T')) AS hora_programada_ts,
        CASE WHEN v.hora_real IS NOT NULL AND v.hora_real != ''
             THEN from_iso8601_timestamp(replace(v.hora_real, ' ', 'T')) END AS hora_real_ts
    FROM vuelo v
    WHERE v.estado <> 'Cancelado'
),
clasificados AS (
    SELECT
        id,
        tipo,
        CAST(EXTRACT(HOUR FROM hora_programada_ts) AS INTEGER) AS hora,
        CASE
            WHEN CAST(EXTRACT(HOUR FROM hora_programada_ts) AS INTEGER) BETWEEN 6  AND 8  THEN 'HORA PUNTA (06-09h)'
            WHEN CAST(EXTRACT(HOUR FROM hora_programada_ts) AS INTEGER) BETWEEN 18 AND 20 THEN 'HORA PUNTA (18-21h)'
            ELSE 'NO PUNTA'
        END AS franja,
        CASE
            WHEN estado = 'Retrasado' THEN 1
            WHEN hora_real_ts IS NOT NULL
                 AND date_diff('minute', hora_programada_ts, hora_real_ts) > 15 THEN 1
            ELSE 0
        END AS es_retrasado,
        CASE
            WHEN hora_real_ts IS NOT NULL
            THEN CAST(date_diff('minute', hora_programada_ts, hora_real_ts) AS DOUBLE)
        END AS retraso_min
    FROM base
)
SELECT
    franja,
    tipo,
    COUNT(*)                                    AS vuelos,
    SUM(es_retrasado)                           AS vuelos_retrasados,
    ROUND(100.0 * SUM(es_retrasado) / COUNT(*), 2) AS pct_retrasados,
    ROUND(AVG(retraso_min), 2)                  AS retraso_promedio_min,
    ROUND(approx_percentile(retraso_min, 0.90), 2) AS retraso_p90_min
FROM clasificados
GROUP BY franja, tipo
ORDER BY franja, tipo;
