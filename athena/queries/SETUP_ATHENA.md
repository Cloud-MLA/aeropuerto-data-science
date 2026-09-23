# Setup de Athena — guía paso a paso para DS-11 y DS-12

Este documento explica cómo dejar Athena listo para que MS5 pueda consultar el catálogo `aeropuerto_lake` y las 2 vistas.

**Prerequisito:** DS-04 (bucket S3), DS-05 (VM-INGESTA), DS-06/07/08 (los 3 contenedores de ingesta corriendo con datos en `s3://mla-aeropuerto-lake/raw/msX/`), DS-09 (crawlers Glue ejecutados) y DS-10 (esquemas ajustados).

---

## Paso 1 — Crear el workgroup de Athena (una sola vez)

En AWS Console → Athena → Workgroups → **Create workgroup**:

- **Name:** `primary` (o el que uses; debe coincidir con `ATHENA_WORKGROUP` en MS5).
- **Query result location:** `s3://mla-aeropuerto-lake/athena-results/`
- **Encryption:** default (SSE-S3).
- **Enforce workgroup configuration:** ✅ (para forzar que todas las queries escriban ahí).

Alternativa CLI:

```bash
aws athena create-work-group \
  --name primary \
  --configuration '{
    "ResultConfiguration": {
      "OutputLocation": "s3://mla-aeropuerto-lake/athena-results/"
    },
    "EnforceWorkGroupConfiguration": true
  }'
```

---

## Paso 2 — Verificar que el catálogo Glue está poblado (DS-09/10 OK)

Athena Console → Data → Database → `aeropuerto_lake` → deben aparecer las tablas:

- De MS1: `persona`, `pasajero`, `categoria_migratoria`, `ticket`, `checkin`, `equipaje`.
- De MS2: `aerolinea`, `aeronave`, `asiento`, `empleado`, `tripulacion`, `operativo_tierra`, `vuelo`, `opera_tripulacion`.
- De MS3 (aplanadas): `recurso`, `incidencia`, `incidencia_afecta_recurso`, `incidencia_retrasa_vuelo`, `asignacion`.

Si falta alguna, revisar el crawler correspondiente.

Prueba rápida:

```sql
SELECT * FROM aeropuerto_lake.vuelo LIMIT 5;
SELECT COUNT(*) FROM aeropuerto_lake.ticket;
SELECT COUNT(*) FROM aeropuerto_lake.incidencia;
```

---

## Paso 3 — DS-11: correr las 5 queries Q1-Q5

Abrir cada `athena/*.sql` de esta carpeta y **pegar en el editor de Athena** con el `aeropuerto_lake` seleccionado como database. Ejecutar y verificar que devuelvan filas.

Orden sugerido (más simple primero):

1. `athena/q3_incidencias_combustible_por_aerolinea.sql` — top simple, valida joins ms2+ms3.
2. `athena/q4_recaudacion_tuua_por_categoria.sql` — valida ms1+ms2.
3. `athena/q1_recursos_mas_fallas.sql` — valida ms3 con `date_diff`.
4. `athena/q5_vuelos_hora_punta_retrasados.sql` — valida `EXTRACT(HOUR)` + `date_diff`.
5. `athena/q2_retraso_promedio.sql` — la más compleja (percentiles + franja).

**Guardar la screenshot de cada resultado en `docs/evidencias/athena/`** — es DS-14.

**Nota Q1:** El SQL usa `INTERVAL '7' DAY` hardcoded. Cuando MS5 la llama con `?dias=N`, el cliente sustituye el valor (ver `ms5-analitica-api/app/services/queries.py`).

---

## Paso 4 — DS-12: crear las 2 vistas

En el editor Athena, ejecutar (uno por vez):

1. `views/vw_recaudacion_tuua.sql` → `CREATE OR REPLACE VIEW vw_recaudacion_tuua AS ...`
2. `views/vw_retrasos_hora_punta.sql` → `CREATE OR REPLACE VIEW vw_retrasos_hora_punta AS ...`

Verificar:

```sql
SHOW VIEWS IN aeropuerto_lake;
-- Debe listar vw_recaudacion_tuua y vw_retrasos_hora_punta

SELECT * FROM vw_recaudacion_tuua;
SELECT * FROM vw_retrasos_hora_punta;
```

**Guardar screenshots** para `docs/evidencias/athena/`.

---

## Paso 5 — Habilitar MS5 en producción

Confirmar que en `compose/vm-prod/docker-compose.yml` (repo `aeropuerto-infra-deploy`) MS5 tenga:

```yaml
environment:
  ATHENA_DATABASE: aeropuerto_lake
  ATHENA_OUTPUT: s3://mla-aeropuerto-lake/athena-results/
  ATHENA_WORKGROUP: primary
  AWS_REGION: us-east-1
```

Redeploy: `docker compose pull && docker compose up -d`.

Probar desde afuera:

```bash
curl https://<api-gateway>/api/analitica/incidencias-combustible-por-aerolinea
# Debe devolver JSON con el ranking (LATAM+Copa arriba si el sesgo del seed funcionó)
```

---

## Diferencias con la versión Postgres local

Los `.sql` de esta carpeta son la versión **Athena/Trino** portada de [`../postgres/`](../postgres/) (originales, validados en Hito 1 con `local-postgres/`). Cambios aplicados:

| Postgres | Athena/Trino |
|---|---|
| `EXTRACT(EPOCH FROM (a - b)) / 60.0` | `date_diff('minute', b, a)` |
| `PERCENTILE_CONT(x) WITHIN GROUP (ORDER BY y)` | `approx_percentile(y, x)` |
| `STDDEV_POP` | `stddev` |
| `NOW()` | `current_timestamp` |
| `TIMESTAMPTZ` | `TIMESTAMP` (Glue infiere del CSV) |
| `x::numeric` | `CAST(x AS DECIMAL)` o `DOUBLE` |
| Sin cast en EXTRACT | `CAST(EXTRACT(HOUR ...) AS INTEGER)` |
