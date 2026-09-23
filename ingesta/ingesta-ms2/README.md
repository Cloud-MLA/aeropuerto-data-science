# ingesta-ms2

Contenedor de ingesta para MS2 (Vuelos / Operaciones). Extrae el 100% de las 8 tablas
de PostgreSQL, genera un CSV por tabla y los sube a S3 bajo el prefijo `raw/ms2/`.

Parte del Proyecto Parcial CS2032 — Cloud Computing (2026-2).
Contexto: [`cloud-computing-proyecto`](https://github.com/btoroled/cloud-computing-proyecto).
Dueño: Mariano (DS-07).

## Qué hace

1. Se conecta a PostgreSQL (`vuelos_db`) vía SQLAlchemy.
2. Extrae cada una de las 8 tablas: `aerolinea`, `aeronave`, `asiento`, `empleado`,
   `tripulacion`, `operativo_tierra`, `vuelo`, `opera_tripulacion`.
3. Escribe un CSV plano por tabla en `output/` (carpeta local dentro del contenedor).
4. Sube cada CSV a `s3://<bucket>/raw/ms2/<tabla>/<fecha>/<tabla>.csv`.

Las tablas sin filas igual generan su CSV (solo con encabezado) — no se omiten.

## Tablas

- aerolinea
- aeronave
- asiento
- empleado
- tripulacion
- operativo_tierra
- vuelo
- opera_tripulacion

## Uso

### 1. Configurar variables de entorno

```bash
cp .env.example .env
```

Completa `.env` con:

- Credenciales de conexión a tu PostgreSQL de MS2
- Nombre del bucket S3 y credenciales de AWS (o déjalas vacías si la VM usa un IAM Role)

### 2. Construir la imagen

```bash
docker compose build
```

### 3. Modo de prueba (sin tocar S3)

Genera los CSV localmente en `output/` sin subir nada:

```bash
docker compose run --rm ingesta-ms2 --dry-run
```

### 4. Ejecución real (genera CSV + sube a S3)

```bash
docker compose run --rm ingesta-ms2
```

El log indica, por cada tabla, cuántas filas se leyeron y a qué ruta/key se escribieron —
sirve como evidencia de que filas leídas = filas escritas.

## Estructura en S3

s3://<bucket>/
└── raw/ms2/
├── aerolinea/<fecha>/aerolinea.csv
├── aeronave/<fecha>/aeronave.csv
├── asiento/<fecha>/asiento.csv
├── empleado/<fecha>/empleado.csv
├── tripulacion/<fecha>/tripulacion.csv
├── operativo_tierra/<fecha>/operativo_tierra.csv
├── vuelo/<fecha>/vuelo.csv
└── opera_tripulacion/<fecha>/opera_tripulacion.csv

`<fecha>` es la fecha de ejecución de la ingesta (formato ISO, `YYYY-MM-DD`), no una
fecha de negocio — permite repetir la ingesta sin sobreescribir corridas anteriores.

## Notas sobre credenciales AWS

Si corres esto en el AWS Learner Lab, las credenciales suelen ser temporales e incluyen
un `AWS_SESSION_TOKEN` además del access key / secret key — inclúyelo en tu `.env` o la
subida a S3 fallará con `NoCredentialsError` / `ExpiredToken`.

Si la VM tiene un IAM Role asignado (Instance Profile), puedes dejar
`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` vacíos y boto3 debería resolver las
credenciales automáticamente.

## Dependencia

Requiere que el bucket S3 (`AWS_S3_BUCKET`) ya exista — a cargo de Benja (DS-04).
