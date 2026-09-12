import argparse
import csv
import io
import os
from datetime import date
from pathlib import Path

import boto3
from sqlalchemy import create_engine, text

TABLAS = ["persona", "categoria_migratoria", "pasajero", "ticket", "checkin", "equipaje"]
OUTPUT_LOCAL = Path("output") / "raw" / "ms1"


def get_db_url():
    return (
        f"mysql+pymysql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
    )


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION"),
    )


def extraer_tabla(engine, tabla):
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {tabla}"))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]


def escribir_csv_local(tabla, rows):
    fecha = date.today().isoformat()
    outdir = OUTPUT_LOCAL / tabla / fecha
    outdir.mkdir(parents=True, exist_ok=True)
    ruta = outdir / f"{tabla}.csv"
    with ruta.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {tabla}: {len(rows)} filas -> {ruta}")
    return ruta


def subir_csv_s3(s3, bucket, tabla, rows):
    if not rows:
        print(f"  {tabla}: 0 filas, skip")
        return
    fecha = date.today().isoformat()
    key = f"raw/ms1/{tabla}/{fecha}/{tabla}.csv"
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )
    print(f"  {tabla}: {len(rows)} filas -> s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description="ingesta-ms1: MySQL -> CSV -> S3")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="lee MySQL y escribe CSVs en output/ sin tocar S3",
    )
    args = parser.parse_args()

    engine = create_engine(get_db_url(), pool_pre_ping=True)

    if args.dry_run:
        print("[ingesta-ms1] Modo: DRY-RUN (local, sin S3)")
        for tabla in TABLAS:
            print(f"Extrayendo {tabla}...")
            rows = extraer_tabla(engine, tabla)
            if rows:
                escribir_csv_local(tabla, rows)
        print("[ingesta-ms1] Completado.")
        return

    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET no configurado (DS-04 pendiente)")

    print(f"[ingesta-ms1] Bucket: {bucket}")
    s3 = get_s3_client()
    for tabla in TABLAS:
        print(f"Extrayendo {tabla}...")
        rows = extraer_tabla(engine, tabla)
        subir_csv_s3(s3, bucket, tabla, rows)
    print("[ingesta-ms1] Completado.")


if __name__ == "__main__":
    main()