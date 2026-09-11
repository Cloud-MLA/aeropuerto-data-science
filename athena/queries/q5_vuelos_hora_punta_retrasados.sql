-- Q5 — Porcentaje de vuelos en hora punta retrasados.
--
-- Motivación de negocio: medir si el aeropuerto colapsa en horas pico. La
-- respuesta correcta es comparativa (A/B): hora punta vs. no-punta. Solo
-- reportar el % de hora punta, sin baseline, no dice nada.
--
-- Hora punta: 06-09h y 18-21h (definido en el enunciado).
-- Un vuelo cuenta como "retrasado" si estado = 'Retrasado' O si hora_real -
-- hora_programada > 15 minutos (umbral operacional estandar).
--
-- Endpoint MS5: GET /analitica/vuelos-hora-punta-retrasados
--
-- ATHENA: EXTRACT(HOUR FROM ...) es soportado. EXTRACT(EPOCH FROM ...) se
--         reemplaza por date_diff('minute', ...).

WITH clasificados AS (
    SELECT
        v.id,
        v.tipo,
        EXTRACT(HOUR FROM v.hora_programada)::int AS hora,
        CASE
            WHEN EXTRACT(HOUR FROM v.hora_programada)::int BETWEEN 6  AND 8  THEN 'HORA PUNTA (06-09h)'
            WHEN EXTRACT(HOUR FROM v.hora_programada)::int BETWEEN 18 AND 20 THEN 'HORA PUNTA (18-21h)'
            ELSE 'NO PUNTA'
        END AS franja,
        CASE
            WHEN v.estado = 'Retrasado' THEN 1
            WHEN v.hora_real IS NOT NULL
                 AND EXTRACT(EPOCH FROM (v.hora_real - v.hora_programada)) / 60.0 > 15 THEN 1
            ELSE 0
        END AS es_retrasado,
        CASE
            WHEN v.hora_real IS NOT NULL
            THEN EXTRACT(EPOCH FROM (v.hora_real - v.hora_programada)) / 60.0
        END AS retraso_min
    FROM ms2.vuelo v
    WHERE v.estado <> 'Cancelado'
)
SELECT
    franja,
    tipo,
    COUNT(*)                                    AS vuelos,
    SUM(es_retrasado)                           AS vuelos_retrasados,
    ROUND(100.0 * SUM(es_retrasado) / COUNT(*), 2) AS pct_retrasados,
    ROUND(AVG(retraso_min)::numeric, 2)         AS retraso_promedio_min,
    ROUND(
        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY retraso_min)::numeric,
        2
    )                                           AS retraso_p90_min
FROM clasificados
GROUP BY franja, tipo
ORDER BY franja, tipo;
