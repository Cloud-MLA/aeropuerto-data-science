-- Q3 — Ranking de aerolíneas por incidencias de Falta_Combustible.
-- Motor: AWS Athena (Trino/Presto). Endpoint: GET /api/analitica/incidencias-combustible-por-aerolinea

WITH vuelos_por_aerolinea AS (
    SELECT aerolinea_ruc, COUNT(*) AS total_vuelos
    FROM vuelo
    GROUP BY aerolinea_ruc
),
retrasos_combustible AS (
    SELECT
        v.aerolinea_ruc,
        COUNT(DISTINCT i.id) AS incidencias_combustible,
        COUNT(DISTINCT irv.id_vuelo) AS vuelos_afectados
    FROM incidencia i
    JOIN incidencia_retrasa_vuelo irv ON irv.id_incidencia = i.id
    JOIN vuelo v ON v.id = irv.id_vuelo
    WHERE i.tipo_incidencia = 'Falta_Combustible'
    GROUP BY v.aerolinea_ruc
)
SELECT
    a.ruc,
    a.nombre         AS aerolinea,
    a.alianza,
    v.total_vuelos,
    COALESCE(r.incidencias_combustible, 0) AS incidencias_combustible,
    COALESCE(r.vuelos_afectados, 0)        AS vuelos_afectados,
    ROUND(
        1000.0 * COALESCE(r.vuelos_afectados, 0) / v.total_vuelos,
        2
    ) AS tasa_por_1000_vuelos,
    ROUND(
        100.0 * COALESCE(r.vuelos_afectados, 0) / v.total_vuelos,
        2
    ) AS pct_vuelos_afectados
FROM aerolinea a
JOIN vuelos_por_aerolinea v ON v.aerolinea_ruc = a.ruc
LEFT JOIN retrasos_combustible r ON r.aerolinea_ruc = a.ruc
ORDER BY vuelos_afectados DESC, tasa_por_1000_vuelos DESC;
