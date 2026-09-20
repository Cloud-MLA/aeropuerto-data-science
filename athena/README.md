# athena/ — Consultas de Data Science

Las **5 consultas SQL de negocio** (Q1..Q5) que expone MS5 + las **2 vistas Athena** (`vw_recaudacion_tuua`, `vw_retrasos_hora_punta`). Cierra el requisito de "≥4 consultas Athena con join + ≥2 vistas" del enunciado (§4.7 requerimientos) y `hito2 §4` (DS-11, DS-12).

## Estructura

```
athena/
├── README.md                          este archivo
├── queries/
│   ├── postgres/                      SQL en sintaxis PostgreSQL — validación local (DS-03)
│   │   └── q1..q5.sql
│   ├── athena/                        SQL en sintaxis Athena/Trino — listo para pegar (DS-11)
│   │   └── q1..q5.sql
│   ├── views/                         DDL de las 2 vistas Athena (DS-12)
│   │   ├── vw_recaudacion_tuua.sql
│   │   └── vw_retrasos_hora_punta.sql
│   └── SETUP_ATHENA.md                guía paso a paso: workgroup + correr Q1-Q5 + crear vistas
├── expected/                          resultados de referencia (Postgres, SEED=20260905)
└── local-postgres/                    Docker + schema + carga para validar en local (DS-03)
    ├── docker-compose.yml, schema.sql, aplanar_ms3.py, load.sh, run_queries.sh
```

## Cuál es cuál — Q1 a Q5

| # | Endpoint MS5 | Pregunta de negocio | Postgres (local) | Athena (producción) |
|---|---|---|---|---|
| Q1 | `/analitica/recursos-mas-fallas?dias=` | Recurso con más incidencias en N días | [`queries/postgres/q1_*.sql`](queries/postgres/q1_recursos_mas_fallas.sql) | [`queries/athena/q1_*.sql`](queries/athena/q1_recursos_mas_fallas.sql) |
| Q2 | `/analitica/retraso-promedio?tipo=` | Retraso medio por tipo + percentiles | [`postgres/q2`](queries/postgres/q2_retraso_promedio.sql) | [`athena/q2`](queries/athena/q2_retraso_promedio.sql) |
| Q3 | `/analitica/incidencias-combustible-por-aerolinea` | Ranking Falta_Combustible por aerolínea | [`postgres/q3`](queries/postgres/q3_incidencias_combustible_por_aerolinea.sql) | [`athena/q3`](queries/athena/q3_incidencias_combustible_por_aerolinea.sql) |
| Q4 | `/analitica/recaudacion-tuua-por-categoria` | Recaudación TUUA por categoría | [`postgres/q4`](queries/postgres/q4_recaudacion_tuua_por_categoria.sql) | [`athena/q4`](queries/athena/q4_recaudacion_tuua_por_categoria.sql) · vista [`vw_recaudacion_tuua`](queries/views/vw_recaudacion_tuua.sql) |
| Q5 | `/analitica/vuelos-hora-punta-retrasados` | % vuelos hora punta retrasados | [`postgres/q5`](queries/postgres/q5_vuelos_hora_punta_retrasados.sql) | [`athena/q5`](queries/athena/q5_vuelos_hora_punta_retrasados.sql) · vista [`vw_retrasos_hora_punta`](queries/views/vw_retrasos_hora_punta.sql) |

Cada query cruza **al menos 2 de los 3 microservicios** — Q1 (MS3), Q2 (MS2 + aerolínea), Q3 (MS2 + MS3), Q4 (MS1 + MS2), Q5 (MS2).

---

## Validación local con Postgres (DS-03, ya completado)

Requisitos: **Docker Desktop** + Python 3.12 (para aplanar el JSONL de MS3).

```bash
cd ../seeds && py generar.py                        # 1. generar CSV/JSONL con SEED fijo
cd ../athena/local-postgres && docker compose up -d # 2. levantar Postgres 16
bash load.sh                                         # 3. aplanar MS3 + \COPY (~40 seg)
bash run_queries.sh                                  # 4. correr Q1-Q5 y guardar en ../expected/
docker compose down -v                               # 5. limpiar
```

Cliente SQL directo: `host=localhost port=5432 db=aeropuerto_lake user=aeropuerto pass=aeropuerto_dev`.

## Portar a Athena en producción (DS-11 + DS-12)

Ver la **guía completa** en [`queries/SETUP_ATHENA.md`](queries/SETUP_ATHENA.md). Resumen:

1. Verificar catálogo Glue `aeropuerto_lake` con las 15+ tablas (DS-09/10 hecho por Fabricio).
2. Crear workgroup Athena `primary` con output `s3://mla-aeropuerto-lake/athena-results/`.
3. Pegar cada `queries/athena/*.sql` en el editor Athena — verificar que devuelvan filas (DS-11).
4. Ejecutar `queries/views/*.sql` para crear las 2 vistas (DS-12).
5. Guardar screenshots en `docs/evidencias/athena/` (DS-14).

MS5 ya está preparado para consumir esto sin cambios de código — solo requiere las env vars ya configuradas en el compose de producción.

---

## Portabilidad Postgres → Athena

Las 2 versiones (`postgres/` y `athena/`) devuelven **los mismos resultados** contra el mismo seed. Diferencias sintácticas aplicadas al portar:

| Postgres | Athena (Trino/Presto) |
|---|---|
| `NOW() - INTERVAL '7' DAY` | `current_timestamp - INTERVAL '7' DAY` |
| `EXTRACT(EPOCH FROM (a - b)) / 60.0` | `date_diff('minute', b, a)` |
| `PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY x)` | `approx_percentile(x, 0.9)` |
| `STDDEV_POP(x)` | `stddev(x)` |
| `x::numeric` | `CAST(x AS DECIMAL)` o `DOUBLE` |
| `EXTRACT(HOUR FROM x)::int` | `CAST(EXTRACT(HOUR FROM x) AS INTEGER)` |
| `TIMESTAMPTZ` | `TIMESTAMP` (Glue infiere del CSV) |

---

## Hallazgos (para el informe)

Ejecutar las queries sobre los seeds (`SEED=20260905`) revela cosas útiles:

- **Q3 confirma el sesgo del generador**: LATAM Airlines Peru (89.13% de sus vuelos afectados, tasa 891.27 por mil) y Copa Airlines (89.90%, tasa 899.00) concentran el **100%** de las incidencias de `Falta_Combustible`; las otras 22 aerolíneas tienen 0. Ranking claro para el docente.
- **Q4 preserva la distribución migratoria del contrato**: 60% Nacional, 35% Internacional, 5% Tránsito en pasajeros efectivos. Pero por tarifa TUUA (12.50 / 38.45 / 18.00), **Internacional recauda 61% del total** aunque solo aporta 35% de pasajeros.
- **Q1 saca al frente 6 radares y 4 mangas** con 50-60 incidencias en la última semana y TPR ~2200 min (~37 h). `%_abiertas` entre 19% y 37% — alineado con `PCT_INCIDENCIA_ABIERTA=30%` del seed.
- **Q2 muestra que American Airlines y United tienen el peor retraso promedio** (~32 min) en internacionales, P90 ~90 min. Franja **Noche (18-24h)** es la peor (29.18 min vs 26.72 en madrugada).
- **Q5 no muestra diferencia entre hora punta y no punta** (~38-39% en ambas). Es un hallazgo del **generador**, no de la query: el seed sesga la hora pero no correlaciona el estado del vuelo con la hora. En Athena con datos de ingesta real esperamos ver la diferencia. **No es un bug de la query.**

Ver `expected/*.txt` para las salidas completas de Postgres local.
