-- Q5 — % de vuelos en hora punta retrasados (comparativa A/B).
-- Motor: AWS Athena (Trino/Presto). Endpoint: GET /api/analitica/vuelos-hora-punta-retrasados
-- En producción MS5 consulta la vista vw_retrasos_hora_punta (ver views/).

WITH clasificados AS (
    SELECT
        v.id,
        v.tipo,
        CAST(EXTRACT(HOUR FROM v.hora_programada) AS INTEGER) AS hora,
        CASE
            WHEN CAST(EXTRACT(HOUR FROM v.hora_programada) AS INTEGER) BETWEEN 6  AND 8  THEN 'HORA PUNTA (06-09h)'
            WHEN CAST(EXTRACT(HOUR FROM v.hora_programada) AS INTEGER) BETWEEN 18 AND 20 THEN 'HORA PUNTA (18-21h)'
            ELSE 'NO PUNTA'
        END AS franja,
        CASE
            WHEN v.estado = 'Retrasado' THEN 1
            WHEN v.hora_real IS NOT NULL
                 AND date_diff('minute', v.hora_programada, v.hora_real) > 15 THEN 1
            ELSE 0
        END AS es_retrasado,
        CASE
            WHEN v.hora_real IS NOT NULL
            THEN CAST(date_diff('minute', v.hora_programada, v.hora_real) AS DOUBLE)
        END AS retraso_min
    FROM vuelo v
    WHERE v.estado <> 'Cancelado'
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
