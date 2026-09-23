import argparse
import csv
import os
from datetime import date
from pathlib import Path

import boto3
from sqlalchemy import create_engine, text


TABLAS = [
    "aerolinea",
    "aeronave",
    "asiento",
    "empleado",
    "tripulacion",
    "operativo_tierra",
    "vuelo",
    "opera_tripulacion",
]

OUTPUT_DIR = Path("output")  # carpeta plana, sin subdirectorios


def get_db_url():
    return (
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
    )


def get_s3_client():
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or None
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or None

    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.getenv("AWS_REGION"),
    )


def extraer_tabla(engine, tabla):
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {tabla}"))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return columns, rows


def escribir_csv(tabla, columns, rows):
    OUTPUT_DIR.mkdir(exist_ok=True)
    ruta = OUTPUT_DIR / f"{tabla}.csv"

    with ruta.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  {tabla}: {len(rows)} filas -> {ruta}")
    return ruta


def subir_a_s3(s3, bucket, ruta, tabla):
    fecha = date.today().isoformat()
    key = f"raw/ms2/{tabla}/{fecha}/{tabla}.csv"

    s3.upload_file(str(ruta), bucket, key)

    print(f"  {tabla}: subido -> s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description="ingesta-ms2: PostgreSQL -> CSV -> S3")
    parser.add_argument("--dry-run", action="store_true", help="genera los CSV en output/ sin subir a S3")
    args = parser.parse_args()

    engine = create_engine(get_db_url(), pool_pre_ping=True)

    if args.dry_run:
        print("[ingesta-ms2] Modo: DRY-RUN (local, sin S3)")
        for tabla in TABLAS:
            print(f"Extrayendo {tabla}...")
            columns, rows = extraer_tabla(engine, tabla)
            escribir_csv(tabla, columns, rows)
        print("[ingesta-ms2] Completado.")
        return

    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET no configurado (DS-04 pendiente)")

    print(f"[ingesta-ms2] Bucket: {bucket}")
    s3 = get_s3_client()

    for tabla in TABLAS:
        print(f"Extrayendo {tabla}...")
        columns, rows = extraer_tabla(engine, tabla)
        ruta = escribir_csv(tabla, columns, rows)
        subir_a_s3(s3, bucket, ruta, tabla)

    print("[ingesta-ms2] Completado.")


if __name__ == "__main__":
    main()