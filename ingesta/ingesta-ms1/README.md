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

En VM-INGESTA solo se necesita el `docker-compose.yml` (genérico, sin datos
sensibles) y el código del contenedor. El `.env` con host/credenciales de la
DB **no se sube a S3 ni se versiona**: se crea directo en la instancia con
`tee`, igual que en VM-DB/VM-PROD:

```sh
# en VM-INGESTA, dentro de la carpeta del proyecto (p.ej. /opt/ingesta)
tee .env > /dev/null <<'EOF'
DB_HOST=<host-mysql-ms1>
DB_PORT=3306
DB_USER=pasajeros_user
DB_PASSWORD=<password>
DB_NAME=pasajeros_db
AWS_S3_BUCKET=<bucket>
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
EOF
```

```sh
# con el .env lleno: bucket + credenciales AWS
python ingesta.py            # sube los 6 CSVs a s3://<bucket>/raw/ms1/...

# o con Docker
docker build -t ingesta-ms1 .
docker run --env-file .env ingesta-ms1

# o con docker compose (recomendado en VM-INGESTA)
docker compose run --rm ingesta            # corrida real
docker compose run --rm ingesta --dry-run  # valida conexión a MySQL sin tocar S3
```

Es un job one-shot: corre, sube los CSVs y termina (no queda como servicio
persistente). Para correrlo a diario, agenda `docker compose run --rm ingesta`
con cron en VM-INGESTA en vez de dejar el contenedor con `restart: always`.

En VM-INGESTA con LabRole (instance profile), dejar `AWS_ACCESS_KEY_ID` y
`AWS_SECRET_ACCESS_KEY` vacíos en el `.env` — boto3 toma las credenciales del
rol de la instancia automáticamente. Solo hace falta `AWS_S3_BUCKET` y
`AWS_REGION`.

Formato bucket/credenciales según lo que entregue el Lead (DS-04/DS-05).