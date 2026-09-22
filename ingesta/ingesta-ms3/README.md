# ingesta-ms3

Contenedor de ingesta del MS3 (infraestructura): lee el 100% de las colecciones
de `infra_db` (MongoDB) y sube **5 archivos planos** a S3 en
`raw/ms3/<tabla>/<fecha>/<tabla>.csv`.

El aplanamiento de `incidencias` (anidada) replica la lógica ya escrita en
`athena/local-postgres/aplanar_ms3.py` y el esquema de
`athena/local-postgres/schema.sql` (mismos archivos y columnas).

| Archivo                     | Origen en Mongo        | Columnas |
|-----------------------------|------------------------|----------|
| `recurso.csv`               | `recursos` (1 fila/doc)| `id`, `nombre_tecnico_locacion`, `tipo`, `estado_acople`, `longitud`, `clase_max`, `rango_alcance`, `frecuencia` |
| `incidencia.csv`            | `incidencias` (base)   | `id`, `gravedad`, `descripcion`, `tipo_incidencia`, `fecha_reporte`, `fecha_cierre` |
| `incidencia_afecta_recurso.csv` | `incidencias.afecta_recursos[]` (rompe array) | `id_incidencia`, `id_recurso` |
| `incidencia_retrasa_vuelo.csv` | `incidencias.retrasa_vuelos[]` (rompe array) | `id_incidencia`, `id_vuelo` |
| `asignacion.csv`            | `asignaciones` (1 fila/doc) | `id_vuelo`, `id_recurso` |

Las fechas se serializan como ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`) y `null`
como campo vacío.

## Dependencias (DS)

- **DS-04**: bucket S3 (lo crea el Lead).
- **DS-05**: VM-INGESTA con credenciales AWS (access key / secret / region).
- BD MS3 en MongoDB (`infra_db`) ya cargada (ver "Carga del seed").

## Pasos realizados (MS3-08 + DS-08)

### 1. Generar el seed (MS3-08)

Desde este repo (`aeropuerto-data-science/`), el generador compartido del data
squad (SEED determinista `20260905`, volúmenes en `seeds/config.py`):

```sh
# MS2 primero: MS1 y MS3 muestrean vuelo_id del output de MS2
python seeds/generar.py --ms 2
python seeds/generar.py --ms 3
```

Salida: `seeds/output/ms3/{recursos,incidencias,asignaciones}.jsonl`
(500 recursos = 350 mangas + 150 radares; 25 000 incidencias; 40 000 asignaciones).
Los 65 500 docs pasan el AJV del modelo MS3 (validación local, 0 fallos).

### 2. Cargar a MongoDB (`infra_db`)

Con el Mongo de MS3 corriendo (`docker compose up -d ms3_mongo_db`):

```sh
docker cp seeds/output/ms3/recursos.jsonl   ms3_mongo_db:/tmp/recursos.jsonl
docker cp seeds/output/ms3/incidencias.jsonl ms3_mongo_db:/tmp/incidencias.jsonl
docker cp seeds/output/ms3/asignaciones.jsonl ms3_mongo_db:/tmp/asignaciones.jsonl

docker exec ms3_mongo_db mongoimport --db infra_db --collection recursos    --drop --file /tmp/recursos.jsonl
docker exec ms3_mongo_db mongoimport --db infra_db --collection incidencias --drop --file /tmp/incidencias.jsonl
docker exec ms3_mongo_db mongoimport --db infra_db --collection asignaciones --drop --file /tmp/asignaciones.jsonl
```

> `--drop` garantiza que `infra_db` sea **exactamente** el seed determinista.
> En la primera carga (sin `--drop`) se detectaron docs de prueba con ids que
> colisionaban con el seed (recurso `1`, `351`, incidencia `1`) y un texto con
> caracteres corruptos (`U+FFFD`); se hizo el import limpio y se verificó
> `0` docs con `U+FFFD`.

### 3. Evidencia (MS3-08)

```sh
docker exec ms3_mongo_db mongosh --quiet infra_db --eval \
  "print('recursos:', db.recursos.countDocuments());
   print('incidencias:', db.incidencias.countDocuments());
   print('asignaciones:', db.asignaciones.countDocuments())"
# recursos: 500 | incidencias: 25000 | asignaciones: 40000  -> incidencias >= 20000 OK
```

### 4. Ingesta local (dry-run, sin S3)

```sh
cd ingesta/ingesta-ms3
pip install -r requirements.txt     # pymongo + boto3
python ingesta.py --dry-run
```

Salida en `output/raw/ms3/<tabla>/<fecha>/<tabla>.csv` (solo lectura, no toca S3).

Resultado medido en esta corrida:

```
recursos                : 500 docs -> recurso.csv
incidencias             : 25000 docs -> incidencia.csv
incidencia_afecta_recurso: 50136 filas (= suma de arrays en Mongo)
incidencia_retrasa_vuelo: 46678 filas (= suma de arrays en Mongo)
asignaciones            : 40000 docs -> asignacion.csv
```

DoD de la ingesta: pull del 100% de cada colección, filas leídas = filas escritas,
salida con código 0.

### 5. Ingesta a S3 (VM-INGESTA, producción)

```sh
cp .env.example .env      # llenar MONGO_HOST, bucket y credenciales AWS
python ingesta.py         # sube los 5 CSVs a s3://<bucket>/raw/ms3/...
# o con Docker:
docker build -t ingesta-ms3 .
docker run --rm --env-file .env ingesta-ms3
```

Desde Docker contra Mongo del host:

```sh
docker run --rm \
  -e MONGO_HOST=host.docker.internal -e MONGO_PORT=27017 -e MONGO_DB=infra_db \
  ingesta-ms3 --dry-run
```

## Verificar consistencia (CSV vs Mongo)

```js
// en mongosh de infra_db
db.incidencias.aggregate([{ $group: { _id: null,
  afecta:  { $sum: { $size: { $ifNull: ["$afecta_recursos", []] } } },
  retrasa: { $sum: { $size: { $ifNull: ["$retrasa_vuelos", []] } } } } }])
```

Los conteos deben coincidir con las filas de `incidencia_afecta_recurso.csv` y
`incidencia_retrasa_vuelo.csv` (50 136 y 46 678 en este seed).

## Siguiente paso (del Lead / Data squad)

Crawler de Glue sobre `s3://<bucket>/raw/ms3/` -> catálogo -> Athena (Q1-Q3), con
joins sobre `incidencia_afecta_recurso` / `incidencia_retrasa_vuelo` usando
`id_incidencia`, `id_recurso` e `id_vuelo` (los nombres de columna quedan fijos
por `schema.sql`).