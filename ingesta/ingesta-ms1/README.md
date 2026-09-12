# ingesta-ms1

Contenedor de ingesta del MS1 (pasajeros): lee las 6 tablas de `pasajeros_db`
(MySQL) y sube un CSV por tabla a S3 en `raw/ms1/<tabla>/<fecha>/<tabla>.csv`.

Formato de fecha del folder: `YYYY-MM-DD`. Tablas: `persona`,
`categoria_migratoria`, `pasajero`, `ticket`, `checkin`, `equipaje`.

## Dependencias (DS)

- **DS-04** bucket S3 (lo crea el Lead).
- **DS-05** VM-INGESTA con credenciales AWS (access key / secret / region).
- BD MS1 en MySQL (`pasajeros_user`).

## Ejecución local (dry-run, sin S3)

Con el compose de MS1 publicado en `localhost:3306`:

```sh
cp .env.example .env   # llenar DB_HOST=localhost
pip install -r requirements.txt
python ingesta.py --dry-run
```

Salida: `output/raw/ms1/<tabla>/<fecha>/<tabla>.csv` (solo lectura, no toca S3).

## Ejecución real a S3 (VM-INGESTA)

```sh
# con el .env lleno: bucket + credenciales AWS
python ingesta.py            # sube los 6 CSVs a s3://<bucket>/raw/ms1/...
# o con Docker
docker build -t ingesta-ms1 .
docker run --env-file .env ingesta-ms1
```

Formato bucket/credenciales según lo que entregue el Lead (DS-04/DS-05).