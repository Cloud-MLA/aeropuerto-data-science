-- Q3 — Ranking de aerolíneas por incidencias de Falta_Combustible.
--
-- Motivación de negocio: identificar responsable logístico. Contar incidencias
-- absolutas no basta — una aerolínea grande naturalmente tendrá más. La
-- métrica comparable es la **tasa por 1000 vuelos**. Incluimos también la
-- alianza global (Star Alliance / SkyTeam / Oneworld) para contexto sectorial.
--
-- Endpoint MS5: GET /analitica/incidencias-combustible-por-aerolinea
--
-- ATHENA: sintaxis estándar, no requiere cambios.

WITH vuelos_por_aerolinea AS (
    SELECT ruc_aerolinea, COUNT(*) AS total_vuelos
    FROM ms2.vuelo
    GROUP BY ruc_aerolinea
),
retrasos_combustible AS (
    SELECT
        v.ruc_aerolinea,
        COUNT(DISTINCT i.id) AS incidencias_combustible,
        COUNT(DISTINCT irv.id_vuelo) AS vuelos_afectados
    FROM ms3.incidencia i
    JOIN ms3.incidencia_retrasa_vuelo irv ON irv.id_incidencia = i.id
    JOIN ms2.vuelo v ON v.id = irv.id_vuelo
    WHERE i.tipo_incidencia = 'Falta_Combustible'
    GROUP BY v.ruc_aerolinea
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
FROM ms2.aerolinea a
JOIN vuelos_por_aerolinea v ON v.ruc_aerolinea = a.ruc
LEFT JOIN retrasos_combustible r ON r.ruc_aerolinea = a.ruc
ORDER BY vuelos_afectados DESC, tasa_por_1000_vuelos DESC;
