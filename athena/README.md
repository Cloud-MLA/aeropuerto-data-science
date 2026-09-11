# athena/ — Consultas de Data Science

Las **5 consultas SQL de negocio** (Q1..Q5) que expone MS5 y que satisfacen el requisito de "≥4 consultas Athena con join" del enunciado (§4.7 requerimientos).

En F0 se validan en **Postgres local** (más rápido que Athena para iterar). En F2 se portan a Athena — la sintaxis es 95% igual, los cambios necesarios están anotados en cada `.sql` como `-- ATHENA: <cambio>`.

## Cuál es cuál

| # | Endpoint MS5 | Pregunta de negocio | Archivo |
|---|---|---|---|
| Q1 | `/analitica/recursos-mas-fallas?dias=` | Recurso (manga/radar) con más incidencias en la última semana | [`queries/q1_recursos_mas_fallas.sql`](queries/q1_recursos_mas_fallas.sql) |
| Q2 | `/analitica/retraso-promedio?tipo=` | Retraso medio de vuelos por tipo, con percentiles | [`queries/q2_retraso_promedio.sql`](queries/q2_retraso_promedio.sql) |
| Q3 | `/analitica/incidencias-combustible-por-aerolinea` | Ranking de aerolíneas por incidencias de `Falta_Combustible` | [`queries/q3_incidencias_combustible_por_aerolinea.sql`](queries/q3_incidencias_combustible_por_aerolinea.sql) |
| Q4 | `/analitica/recaudacion-tuua-por-categoria` | Recaudación TUUA por categoría migratoria | [`queries/q4_recaudacion_tuua_por_categoria.sql`](queries/q4_recaudacion_tuua_por_categoria.sql) |
| Q5 | `/analitica/vuelos-hora-punta-retrasados` | % de vuelos hora punta (06-09h / 18-21h) retrasados | [`queries/q5_vuelos_hora_punta_retrasados.sql`](queries/q5_vuelos_hora_punta_retrasados.sql) |

Cada query cruza **al menos 2 de los 3 microservicios** — Q1 (MS3), Q2 (MS2 + MS2.aerolinea), Q3 (MS2 + MS3), Q4 (MS1 + MS2), Q5 (MS2).

## Cómo reproducir localmente

Requisitos: **Docker Desktop** corriendo + Python 3.12 (para aplanar el JSONL de MS3).

```bash
# 1. Generar los CSV/JSONL con seed fijo (si no lo tienes ya).
cd ../seeds && py generar.py

# 2. Levantar Postgres 16 en Docker (schema.sql se aplica solo al primer boot).
cd ../athena/local-postgres && docker compose up -d

# 3. Aplanar JSONL de MS3 y hacer \COPY de todos los CSVs (~40 seg).
bash load.sh

# 4. Ejecutar Q1..Q5 y guardar la salida en ../expected/.
bash run_queries.sh

# 5. Apagar y borrar el contenedor y volumen.
docker compose down -v
```

También puedes conectarte con tu cliente SQL favorito (DBeaver, TablePlus):

```
host:     localhost
port:     5432
database: aeropuerto_lake
user:     aeropuerto
password: aeropuerto_dev
```

## Estructura

```
athena/
├── README.md                          este archivo
├── queries/                           SQL de las 5 queries (portables a Athena)
├── expected/                          resultados de referencia con el SEED fijo
└── local-postgres/
    ├── docker-compose.yml             postgres 16 alpine + volumen a ../../seeds/output
    ├── schema.sql                     schemas ms1/ms2/ms3 + 15 tablas
    ├── aplanar_ms3.py                 JSONL → CSVs para MS3 (usado también por ingesta-ms3 en F2)
    ├── load.sh                        \COPY de todo (~460k filas en total)
    └── run_queries.sh                 corre Q1..Q5 y guarda salidas
```

## Portabilidad Postgres → Athena

Las 5 queries usan SQL estándar. Los únicos ajustes que hay que hacer al portar:

| Postgres | Athena (Trino/Presto) |
|---|---|
| `NOW() - INTERVAL '7' DAY` | `current_timestamp - INTERVAL '7' DAY` |
| `EXTRACT(EPOCH FROM (a - b)) / 60.0` | `date_diff('minute', b, a)` |
| `STDDEV_POP(x)` | `stddev(x)` (Trino no distingue pop/samp por default) |
| `x::numeric` (casts con `::`) | `CAST(x AS DECIMAL)` |
| `TIMESTAMPTZ` | `TIMESTAMP` (Glue infiere del CSV) |

`PERCENTILE_CONT(...) WITHIN GROUP (ORDER BY ...)` funciona idéntico en ambos.

Cada `.sql` tiene un bloque de comentarios `-- ATHENA:` con los cambios exactos que aplican a esa query.

## Hallazgos (para el informe)

Ejecutar las queries sobre los seeds (`SEED=20260905`) revela cosas útiles del generador:

- **Q3 confirma el sesgo del generador**: LATAM Airlines Peru (89.13% de sus vuelos afectados, tasa 891.27 por mil) y Copa Airlines (89.90%, tasa 899.00) concentran el **100%** de las incidencias de `Falta_Combustible`; las otras 22 aerolíneas tienen 0. Es el ranking claro que el enunciado pide.
- **Q4 preserva la distribución migratoria del contrato**: 60% Nacional, 35% Internacional, 5% Tránsito en pasajeros efectivos. Pero por tarifa TUUA (12.50 / 38.45 / 18.00), **Internacional recauda 61% del total** aunque solo aporta 35% de pasajeros — dato interesante para el dashboard.
- **Q1 saca al frente 6 radares y 4 mangas** con 50-60 incidencias en la última semana y TPR (tiempo promedio de reparación) de ~2200 min (~37 h). El % de incidencias abiertas oscila entre 19% y 37% — todos por debajo del PCT_INCIDENCIA_ABIERTA=30% del seed, con varianza natural.
- **Q2 muestra que American Airlines y United tienen el peor retraso promedio** (~32 min) en internacionales, con P90 alrededor de 90 min. Franja **Noche (18-24h)** tiene el peor retraso promedio (29.18 min vs 26.72 en madrugada).
- **Q5 no muestra diferencia entre hora punta y no punta** (~38-39% retrasados en ambas). Es un hallazgo del generador, no de las queries: el `seeds/config.py` sesga la **hora** de los vuelos hacia horas pico (55%), pero no correlaciona el `estado` de vuelo (`Retrasado`) con la hora. En Athena con datos de ingesta real esperamos ver la diferencia real; para reforzarlo en el seed sintético habría que ajustar `ms2_vuelos.py`. **No es un bug de la query** — la query es correcta.

## Vistas Athena (DS-12, F2)

Q4 se materializará como `vw_recaudacion_tuua`, Q5 como `vw_retrasos_hora_punta` — MS5-06 y MS5-07 las consumen. Se crean en F2 sobre Athena; el SQL se puede derivar directamente de `q4_*.sql` y `q5_*.sql` cambiando `SELECT ...` por `CREATE OR REPLACE VIEW nombre AS SELECT ...`.

Se dejaron fuera de este PR para acotar el alcance a DS-03 (validar la lógica).
