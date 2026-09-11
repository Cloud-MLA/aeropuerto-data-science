"""Aplana los JSONL de MS3 (MongoDB) a CSV para poder cargarlos en Postgres/Athena.

Este mismo aplanamiento lo hara el contenedor ingesta-ms3 en F2 (DS-08).

Entradas (producidas por seeds/generar.py --ms 3):
    seeds/output/ms3/recursos.jsonl
    seeds/output/ms3/incidencias.jsonl
    seeds/output/ms3/asignaciones.jsonl

Salidas:
    seeds/output/ms3-flat/recurso.csv
    seeds/output/ms3-flat/incidencia.csv
    seeds/output/ms3-flat/incidencia_afecta_recurso.csv
    seeds/output/ms3-flat/incidencia_retrasa_vuelo.csv
    seeds/output/ms3-flat/asignacion.csv
"""
import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "seeds" / "output"
SRC = BASE / "ms3"
DST = BASE / "ms3-flat"


def _open_csv(name: str, header: list[str]):
    path = DST / f"{name}.csv"
    f = path.open("w", encoding="utf-8", newline="")
    w = csv.writer(f)
    w.writerow(header)
    return f, w


def aplanar_recursos() -> int:
    f, w = _open_csv(
        "recurso",
        ["id", "nombre_tecnico_locacion", "tipo",
         "estado_acople", "longitud", "clase_max",
         "rango_alcance", "frecuencia"],
    )
    with (SRC / "recursos.jsonl").open("r", encoding="utf-8") as src:
        for n, linea in enumerate(src, 1):
            d = json.loads(linea)
            manga = d.get("manga") or {}
            radar = d.get("radar") or {}
            w.writerow([
                d["id"], d["nombre_tecnico_locacion"], d["tipo"],
                manga.get("estado_acople", ""), manga.get("longitud", ""), manga.get("clase_max", ""),
                radar.get("rango_alcance", ""), radar.get("frecuencia", ""),
            ])
    f.close()
    return n


def aplanar_incidencias() -> tuple[int, int, int]:
    f_i, w_i = _open_csv(
        "incidencia",
        ["id", "gravedad", "descripcion", "tipo_incidencia", "fecha_reporte", "fecha_cierre"],
    )
    f_ar, w_ar = _open_csv("incidencia_afecta_recurso", ["id_incidencia", "id_recurso"])
    f_rv, w_rv = _open_csv("incidencia_retrasa_vuelo", ["id_incidencia", "id_vuelo"])

    n_i = n_ar = n_rv = 0
    with (SRC / "incidencias.jsonl").open("r", encoding="utf-8") as src:
        for linea in src:
            d = json.loads(linea)
            w_i.writerow([
                d["id"], d["gravedad"], d["descripcion"], d["tipo_incidencia"],
                d["fecha_reporte"], d["fecha_cierre"] or "",
            ])
            n_i += 1
            for r in d.get("afecta_recursos", []):
                w_ar.writerow([d["id"], r["recurso_id"]])
                n_ar += 1
            for v in d.get("retrasa_vuelos", []):
                w_rv.writerow([d["id"], v["vuelo_id"]])
                n_rv += 1

    for f in (f_i, f_ar, f_rv):
        f.close()
    return n_i, n_ar, n_rv


def aplanar_asignaciones() -> int:
    f, w = _open_csv("asignacion", ["id_vuelo", "id_recurso"])
    with (SRC / "asignaciones.jsonl").open("r", encoding="utf-8") as src:
        n = 0
        for linea in src:
            d = json.loads(linea)
            w.writerow([d["vuelo_id"], d["recurso_id"]])
            n += 1
    f.close()
    return n


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    print(f"Aplanando desde {SRC} -> {DST}")

    n_recursos = aplanar_recursos()
    print(f"  recurso.csv                   : {n_recursos:>7} filas")

    n_i, n_ar, n_rv = aplanar_incidencias()
    print(f"  incidencia.csv                : {n_i:>7} filas")
    print(f"  incidencia_afecta_recurso.csv : {n_ar:>7} filas")
    print(f"  incidencia_retrasa_vuelo.csv  : {n_rv:>7} filas")

    n_asig = aplanar_asignaciones()
    print(f"  asignacion.csv                : {n_asig:>7} filas")


if __name__ == "__main__":
    main()
