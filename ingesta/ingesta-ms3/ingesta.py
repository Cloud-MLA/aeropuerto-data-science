"""ingesta-ms3: MongoDB (recursos/incidencias/asignaciones) -> aplanado -> CSV -> S3.

Job one-shot (no es un servicio), igual que ingesta-ms1/ingesta-ms2. DS-08 del plan.

El aplanado replica exactamente athena/local-postgres/aplanar_ms3.py (Fabricio), la
referencia que ya se habia validado localmente contra los JSONL de seeds/ -- aqui se
lee la misma forma de documento pero desde una MongoDB real en vez de JSONL local.

Uso:
    MONGO_URI=... AWS_S3_BUCKET=... python ingesta.py
    MONGO_URI=... python ingesta.py --dry-run   # escribe CSVs en output/ sin tocar S3
"""
import argparse
import csv
import io
import os
from datetime import date

import boto3
from pymongo import MongoClient

MONGO_URI = os.environ["MONGO_URI"]

TABLAS_RECURSO = ["id", "nombre_tecnico_locacion", "tipo", "estado_acople", "longitud",
                   "clase_max", "rango_alcance", "frecuencia"]
TABLAS_INCIDENCIA = ["id", "gravedad", "descripcion", "tipo_incidencia", "fecha_reporte", "fecha_cierre"]
TABLAS_INCIDENCIA_AFECTA_RECURSO = ["id_incidencia", "id_recurso"]
TABLAS_INCIDENCIA_RETRASA_VUELO = ["id_incidencia", "id_vuelo"]
TABLAS_ASIGNACION = ["id_vuelo", "id_recurso"]


def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # nombre de la BD viene en la URI (mongodb://host:port/infra)
    return client.get_default_database()


def aplanar_recursos(db):
    filas = []
    for d in db.recursos.find({}):
        manga = d.get("manga") or {}
        radar = d.get("radar") or {}
        filas.append({
            "id": d["id"], "nombre_tecnico_locacion": d["nombre_tecnico_locacion"], "tipo": d["tipo"],
            "estado_acople": manga.get("estado_acople", ""), "longitud": manga.get("longitud", ""),
            "clase_max": manga.get("clase_max", ""),
            "rango_alcance": radar.get("rango_alcance", ""), "frecuencia": radar.get("frecuencia", ""),
        })
    return filas


def aplanar_incidencias(db):
    incidencias, afecta_recurso, retrasa_vuelo = [], [], []
    for d in db.incidencias.find({}):
        incidencias.append({
            "id": d["id"], "gravedad": d["gravedad"],
            # El catalogo Glue usa el SerDe simple (field.delim=",") sin soporte de comillas
            # CSV -- una coma dentro del texto libre corre todas las columnas siguientes
            # (ej. tipo_incidencia termina metido en fecha_reporte). Se reemplaza por ";"
            # en vez de cambiar el SerDe, para no romper el tipado (bigint) del resto de
            # columnas que ya funciona con las otras queries.
            "descripcion": d["descripcion"].replace(",", ";"),
            "tipo_incidencia": d["tipo_incidencia"], "fecha_reporte": d["fecha_reporte"],
            "fecha_cierre": d.get("fecha_cierre") or "",
        })
        for r in d.get("afecta_recursos", []):
            afecta_recurso.append({"id_incidencia": d["id"], "id_recurso": r["recurso_id"]})
        for v in d.get("retrasa_vuelos", []):
            retrasa_vuelo.append({"id_incidencia": d["id"], "id_vuelo": v["vuelo_id"]})
    return incidencias, afecta_recurso, retrasa_vuelo


def aplanar_asignaciones(db):
    return [{"id_vuelo": d["vuelo_id"], "id_recurso": d["recurso_id"]} for d in db.asignaciones.find({})]


def escribir_csv_local(tabla, filas, columnas):
    os.makedirs("output", exist_ok=True)
    path = f"output/{tabla}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)
    return path


def subir_csv_s3(s3, bucket, tabla, filas, columnas):
    fecha = date.today().isoformat()
    key = f"raw/ms3/{tabla}/{fecha}/{tabla}.csv"
    buffer = io.StringIO()
    w = csv.DictWriter(buffer, fieldnames=columnas)
    w.writeheader()
    w.writerows(filas)
    s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue().encode("utf-8"), ContentType="text/csv")
    print(f"  {tabla}: {len(filas)} filas -> s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description="ingesta-ms3: MongoDB -> aplanado -> CSV -> S3")
    parser.add_argument("--dry-run", action="store_true", help="escribe CSVs en output/ sin tocar S3")
    args = parser.parse_args()

    db = get_db()
    print(f"[ingesta-ms3] Mongo OK: {db.name}")

    recurso = aplanar_recursos(db)
    incidencia, incidencia_afecta_recurso, incidencia_retrasa_vuelo = aplanar_incidencias(db)
    asignacion = aplanar_asignaciones(db)

    tablas = [
        ("recurso", recurso, TABLAS_RECURSO),
        ("incidencia", incidencia, TABLAS_INCIDENCIA),
        ("incidencia_afecta_recurso", incidencia_afecta_recurso, TABLAS_INCIDENCIA_AFECTA_RECURSO),
        ("incidencia_retrasa_vuelo", incidencia_retrasa_vuelo, TABLAS_INCIDENCIA_RETRASA_VUELO),
        ("asignacion", asignacion, TABLAS_ASIGNACION),
    ]

    if args.dry_run:
        print("[ingesta-ms3] Modo: DRY-RUN (local, sin S3)")
        for tabla, filas, columnas in tablas:
            if filas:
                path = escribir_csv_local(tabla, filas, columnas)
                print(f"  {tabla}: {len(filas)} filas -> {path}")
        print("[ingesta-ms3] Completado.")
        return

    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET no configurado (DS-04 pendiente)")

    print(f"[ingesta-ms3] Bucket: {bucket}")
    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
    )
    for tabla, filas, columnas in tablas:
        subir_csv_s3(s3, bucket, tabla, filas, columnas)
    print("[ingesta-ms3] Completado.")


if __name__ == "__main__":
    main()
