-- Q2 — Retraso promedio de vuelos internacionales, con distribución completa.
--
-- Motivación de negocio: medir SLA operacional. La media puede engañar (unos
-- pocos vuelos con retraso extremo la disparan), por eso incluimos P50, P90,
-- P99 y desviación estándar. Además, desglose por franja horaria para ver si
-- el retraso es más pronunciado en horas pico.
--
-- Endpoint MS5: GET /analitica/retraso-promedio?tipo=Internacional
-- Parámetro `tipo` reemplaza el literal 'Internacional' en el WHERE.
--
-- Solo se consideran vuelos que efectivamente despegaron o aterrizaron
-- (Cancelado y Programado no aportan retraso real medible).
--
-- ATHENA: EXTRACT(EPOCH FROM ...) -> date_diff('minute', hora_programada, hora_real)
-- ATHENA: STDDEV_POP -> stddev; el resto es SQL estándar.

WITH retrasos AS (
    SELECT
        v.id,
        v.num_vuelo,
        v.hora_programada,
        v.ruc_aerolinea,
        EXTRACT(EPOCH FROM (v.hora_real - v.hora_programada)) / 60.0 AS retraso_min,
        CASE EXTRACT(HOUR FROM v.hora_programada)::int / 6
             WHEN 0 THEN 'Madrugada (0-6)'
             WHEN 1 THEN 'Manana (6-12)'
             WHEN 2 THEN 'Tarde (12-18)'
             ELSE       'Noche (18-24)'
        END AS franja_horaria
    FROM ms2.vuelo v
    WHERE v.tipo = 'Internacional'
      AND v.estado IN ('Retrasado', 'Despegado', 'Aterrizado')
      AND v.hora_real IS NOT NULL
)
SELECT
    'GLOBAL' AS grupo,
    'Todo el periodo' AS categoria,
    COUNT(*) AS vuelos,
    ROUND(AVG(retraso_min)::numeric, 2) AS retraso_promedio_min,
    ROUND(STDDEV_POP(retraso_min)::numeric, 2) AS desv_estandar_min,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY retraso_min)::numeric, 2) AS p50,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY retraso_min)::numeric, 2) AS p90,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY retraso_min)::numeric, 2) AS p99
FROM retrasos

UNION ALL

SELECT
    'POR FRANJA' AS grupo,
    franja_horaria,
    COUNT(*),
    ROUND(AVG(retraso_min)::numeric, 2),
    ROUND(STDDEV_POP(retraso_min)::numeric, 2),
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY retraso_min)::numeric, 2),
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY retraso_min)::numeric, 2),
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY retraso_min)::numeric, 2)
FROM retrasos
GROUP BY franja_horaria

UNION ALL

SELECT
    'POR AEROLINEA' AS grupo,
    a.nombre,
    COUNT(*),
    ROUND(AVG(r.retraso_min)::numeric, 2),
    ROUND(STDDEV_POP(r.retraso_min)::numeric, 2),
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY r.retraso_min)::numeric, 2),
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY r.retraso_min)::numeric, 2),
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY r.retraso_min)::numeric, 2)
FROM retrasos r
JOIN ms2.aerolinea a ON a.ruc = r.ruc_aerolinea
GROUP BY a.nombre
HAVING COUNT(*) >= 30      -- filtra aerolineas con muestra representativa
ORDER BY grupo, retraso_promedio_min DESC
LIMIT 100;
