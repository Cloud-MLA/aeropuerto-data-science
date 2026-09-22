import argparse
import boto3
import csv
import io
import os
from datetime import date, datetime, timezone
from pathlib import Path

import pymongo

OUTPUT_LOCAL = Path("output") / "raw" / "ms3"

# (tabla, header) de los 5 archivos planos que deja la ingesta de MS3.
# El aplanado de incidencias replica seeds/../athena/local-postgres/aplanar_ms3.py
# y el schema de athena/local-postgres/schema.sql, con los mismos nombres de archivo.
TABLAS = [
    ("recurso", ["id", "nombre_tecnico_locacion", "tipo", "estado_acople", "longitud", "clase_max", "rango_alcance", "frecuencia"]),
    ("incidencia", ["id", "gravedad", "descripcion", "tipo_incidencia", "fecha_reporte", "fecha_cierre"]),
    ("incidencia_afecta_recurso", ["id_incidencia", "id_recurso"]),
    ("incidencia_retrasa_vuelo", ["id_incidencia", "id_vuelo"]),
    ("asignacion", ["id_vuelo", "id_recurso"]),
]


def get_mongo():
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    db = os.getenv("MONGO_DB", "infra_db")
    client = pymongo.MongoClient(f"mongodb://{host}:{port}/", serverSelectionTimeoutMS=5000)
    return client[db]


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION"),
    )


def _fmt(valor) -> str:
    """Serializa valores Mongo a texto plano (fechas ISO 8601 UTC, null -> vacio)."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(valor)


def leer_recursos(db):
    filas = []
    for doc in db.recursos.find({}, {"_id": 0}):
        manga = doc.get("manga") or {}
        radar = doc.get("radar") or {}
        filas.append([
            doc.get("id", ""), doc.get("nombre_tecnico_locacion", ""), doc.get("tipo", ""),
            manga.get("estado_acople", ""), manga.get("longitud", ""), manga.get("clase_max", ""),
            radar.get("rango_alcance", ""), radar.get("frecuencia", ""),
        ])
    return filas


def leer_incidencias(db):
    """Aplana incidencias (anidadas) en 3 archivos planos."""
    filas_incidencia = []
    filas_afecta = []
    filas_retrasa = []
    for doc in db.incidencias.find({}, {"_id": 0}):
        filas_incidencia.append([
            doc.get("id", ""), doc.get("gravedad", ""), doc.get("descripcion", ""),
            doc.get("tipo_incidencia", ""), _fmt(doc.get("fecha_reporte")), _fmt(doc.get("fecha_cierre")),
        ])
        for r in doc.get("afecta_recursos") or []:
            filas_afecta.append([doc.get("id", ""), (r or {}).get("recurso_id", "")])
        for v in doc.get("retrasa_vuelos") or []:
            filas_retrasa.append([doc.get("id", ""), (v or {}).get("vuelo_id", "")])
    return filas_incidencia, filas_afecta, filas_retrasa


def leer_asignaciones(db):
    filas = []
    for doc in db.asignaciones.find({}, {"_id": 0}):
        filas.append([doc.get("vuelo_id", ""), doc.get("recurso_id", "")])
    return filas


def escribir_csv_local(tabla, header, filas):
    fecha = date.today().isoformat()
    outdir = OUTPUT_LOCAL / tabla / fecha
    outdir.mkdir(parents=True, exist_ok=True)
    ruta = outdir / f"{tabla}.csv"
    with ruta.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(filas)
    print(f"  {tabla}: {len(filas)} filas -> {ruta}")
    return ruta


def subir_csv_s3(s3, bucket, tabla, header, filas):
    if not filas:
        print(f"  {tabla}: 0 filas, skip")
        return
    fecha = date.today().isoformat()
    key = f"raw/ms3/{tabla}/{fecha}/{tabla}.csv"
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(filas)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )
    print(f"  {tabla}: {len(filas)} filas -> s3://{bucket}/{key}")


def extraer_todo(db):
    """Lee el 100% de las colecciones y devuelve {tabla: filas}."""
    recursos = leer_recursos(db)
    inc, afecta, retrasa = leer_incidencias(db)
    asignaciones = leer_asignaciones(db)

    n_incidencias = db.incidencias.count_documents({})
    print("[ingesta-ms3] Lectura desde MongoDB (100%):")
    print(f"  recursos          : {db.recursos.count_documents({})} docs -> 1 archivo plano")
    print(f"  incidencias       : {n_incidencias} docs -> 3 archivos planos")
    print(f"  asignaciones      : {db.asignaciones.count_documents({})} docs -> 1 archivo plano")

    return {
        "recurso": recursos,
        "incidencia": inc,
        "incidencia_afecta_recurso": afecta,
        "incidencia_retrasa_vuelo": retrasa,
        "asignacion": asignaciones,
    }


def main():
    parser = argparse.ArgumentParser(description="ingesta-ms3: MongoDB -> CSV aplanado -> S3")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="lee MongoDB y escribe CSVs en output/ sin tocar S3",
    )
    args = parser.parse_args()

    db = get_mongo()
    datos = extraer_todo(db)

    if args.dry_run:
        print("[ingesta-ms3] Modo: DRY-RUN (local, sin S3)")
        for tabla, header in TABLAS:
            escribir_csv_local(tabla, header, datos[tabla])
        print("[ingesta-ms3] Completado.")
        return

    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET no configurado (DS-04 pendiente)")

    print(f"[ingesta-ms3] Bucket: {bucket}")
    s3 = get_s3_client()
    for tabla, header in TABLAS:
        subir_csv_s3(s3, bucket, tabla, header, datos[tabla])
    print("[ingesta-ms3] Completado.")


if __name__ == "__main__":
    main()