# ingesta-ms3

Contenedor de ingesta MS3 (DS-08): lee las 3 colecciones de MongoDB (`recursos`,
`incidencias`, `asignaciones`), las aplana a 5 tablas relacionales y las sube a
`s3://<bucket>/raw/ms3/<tabla>/<fecha>/<tabla>.csv`.

El aplanado replica exactamente `athena/local-postgres/aplanar_ms3.py` (la referencia
ya validada localmente por Fabricio contra los JSONL de `seeds/`), adaptado para leer
de una MongoDB real en vez de archivos locales.

## Tablas de salida

| Tabla | Origen | Columnas |
|---|---|---|
| `recurso` | `recursos` | id, nombre_tecnico_locacion, tipo, estado_acople, longitud, clase_max, rango_alcance, frecuencia |
| `incidencia` | `incidencias` | id, gravedad, descripcion, tipo_incidencia, fecha_reporte, fecha_cierre |
| `incidencia_afecta_recurso` | `incidencias.afecta_recursos[]` | id_incidencia, id_recurso |
| `incidencia_retrasa_vuelo` | `incidencias.retrasa_vuelos[]` | id_incidencia, id_vuelo |
| `asignacion` | `asignaciones` | id_vuelo, id_recurso |

## Uso

```bash
cp .env.example .env && $EDITOR .env   # MONGO_URI, AWS_S3_BUCKET
docker compose run --rm ingesta            # corrida real, sube a S3
docker compose run --rm ingesta --dry-run  # valida conexion a Mongo, escribe en output/
```

## Cargar el seed en MongoDB (una vez, antes de la primera corrida)

```bash
python seeds/generar.py --ms 3   # genera seeds/output/ms3/{recursos,incidencias,asignaciones}.jsonl
mongoimport --uri "$MONGO_URI" --collection recursos     --file seeds/output/ms3/recursos.jsonl --drop
mongoimport --uri "$MONGO_URI" --collection incidencias  --file seeds/output/ms3/incidencias.jsonl --drop
mongoimport --uri "$MONGO_URI" --collection asignaciones --file seeds/output/ms3/asignaciones.jsonl --drop
```
