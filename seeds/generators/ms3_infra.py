"""Generador de MS3 — Infraestructura / Incidencias (MongoDB).

Colecciones producidas (JSONL — un documento por línea, listo para
`mongoimport --db infra_db --collection <nombre> --file <archivo>.jsonl`):

    - recursos      (500 = 350 mangas + 150 radares, IDs 1..500 — contrato §3)
    - incidencias   (25 000, con arrays afecta_recursos[] y retrasa_vuelos[])
    - asignaciones  (~40 000 pares vuelo ↔ recurso — colección "Utiliza")

Depende de MS2: lee `output/ms2/vuelo.csv` para muestrear `vuelo_id`
(referencia suave, sin FK física) y usa `ruc_aerolinea` para sesgar
`Falta_Combustible` a las aerolíneas objetivo (AEROLINEAS_CON_MUCHO_COMBUSTIBLE_INDEX)
— así Q3 (aerolínea con más incidencias de combustible) tiene ranking claro.

Los `vuelo_id` que aparezcan en `retrasa_vuelos[]` no fuerzan que el vuelo
esté en estado `Retrasado` en MS2 — el modelo es de referencia suave y en
producción la validación la haría MS3 llamando a MS2. Aquí solo generamos
data consistente en volumen.
"""
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

import config
import catalogos


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _escribir_jsonl(ruta: Path, documentos) -> int:
    """Escribe un iterable de dicts como JSONL (un doc por línea, UTF-8)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with ruta.open("w", encoding="utf-8", newline="\n") as f:
        for doc in documentos:
            f.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
            n += 1
    return n


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_weighted(rng: random.Random, distribucion: dict[str, float]) -> str:
    valores = list(distribucion.keys())
    pesos = list(distribucion.values())
    return rng.choices(valores, weights=pesos, k=1)[0]


def _leer_vuelos_ms2() -> list[dict]:
    """Lee el pool de vuelos generado por MS2, incluyendo ruc_aerolinea."""
    ruta = config.OUTPUT_MS2 / "vuelo.csv"
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta}. Corre 'python generar.py --ms 2' primero."
        )
    vuelos = []
    with ruta.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for fila in r:
            vuelos.append({
                "id": int(fila["id"]),
                "hora_programada": datetime.strptime(
                    fila["hora_programada"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc),
                "estado": fila["estado"],
                "ruc_aerolinea": fila["ruc_aerolinea"],
            })
    return vuelos


# ---------------------------------------------------------------------------
# Colección: recursos
# ---------------------------------------------------------------------------
def _generar_recursos(rng: random.Random) -> list[dict]:
    """350 mangas (IDs 1..350) + 150 radares (IDs 351..500)."""
    recursos = []

    # Mangas
    for i in range(1, config.N_RECURSOS_MANGAS + 1):
        clase_max = rng.choice(catalogos.CLASES_OACI)
        longitud = round(rng.uniform(12.0, 42.0), 2)
        estado = _pick_weighted(rng, {"Libre": 0.55, "Ocupado": 0.35, "Mantenimiento": 0.10})
        recursos.append({
            "id": i,
            "nombre_tecnico_locacion": catalogos.nombre_manga(i - 1),
            "tipo": "manga",
            "manga": {
                "estado_acople": estado,
                "longitud": longitud,
                "clase_max": clase_max,
            },
        })

    # Radares
    for j in range(config.N_RECURSOS_RADARES):
        recurso_id = config.N_RECURSOS_MANGAS + j + 1
        recursos.append({
            "id": recurso_id,
            "nombre_tecnico_locacion": catalogos.nombre_radar(j),
            "tipo": "radar",
            "radar": {
                "rango_alcance": rng.randint(80, 400),  # millas náuticas
                "frecuencia": rng.choice(catalogos.FRECUENCIAS_RADAR),
            },
        })

    _escribir_jsonl(config.OUTPUT_MS3 / "recursos.jsonl", recursos)
    return recursos


# ---------------------------------------------------------------------------
# Colección: incidencias
# ---------------------------------------------------------------------------
# Frases sintéticas por tipo — dan descripciones realistas sin usar Faker
# (Faker en español mete latín macarrónico). Un template + 1-2 variables.
_DESCRIPCIONES_POR_TIPO = {
    "Falla_Radar": [
        "Perdida intermitente de retorno en {frec}",
        "Falla del sistema de barrido primario ({frec})",
        "Radar reporta ecos fantasma tras {min} min de operacion",
    ],
    "Inundacion": [
        "Acumulacion de agua en {zona} tras lluvias intensas",
        "Filtracion mayor en {zona}, riesgo de corto en instalaciones",
        "Colector obstruido, agua superando {cm} cm sobre nivel operativo",
    ],
    "Falta_Combustible": [
        "Aerolinea reporta suministro insuficiente en surtidor {surt}",
        "Retraso en abastecimiento por falla logistica del proveedor",
        "Reserva de Jet A-1 por debajo del minimo operacional",
    ],
    "Saturacion_Vial": [
        "Congestion en calle de rodaje {calle}",
        "Bloqueo temporal en acceso {acc} por vehiculo averiado",
        "Cola de espera en TWY {calle} superior a {min} min",
    ],
    "Manga_Inoperativa": [
        "Falla mecanica en sistema de posicionamiento de manga",
        "Sensor de acople reporta lectura incoherente",
        "Puente de embarque bloqueado por proteccion antimolino",
    ],
    "Otro": [
        "Evento no clasificado — requiere revision del supervisor de turno",
        "Alerta preventiva reportada por sistema {sys}",
        "Anomalia detectada durante inspeccion rutinaria",
    ],
}


def _generar_descripcion(rng: random.Random, tipo: str) -> str:
    template = rng.choice(_DESCRIPCIONES_POR_TIPO[tipo])
    return template.format(
        frec=rng.choice(catalogos.FRECUENCIAS_RADAR),
        zona=rng.choice(["Espigón A", "Espigón B", "Espigón C", "hall central", "zona de rampa"]),
        min=rng.randint(15, 120),
        cm=rng.randint(3, 25),
        surt=rng.randint(1, 12),
        calle=rng.choice(["A1", "B2", "C3", "D4", "E1"]),
        acc=rng.choice(["Norte", "Sur", "Cargas"]),
        sys=rng.choice(["SCADA", "BHS", "FIDS", "GPU"]),
    )


def _pct_retrasa_vuelos_por_tipo(tipo: str) -> float:
    """Probabilidad de que una incidencia de este tipo retrase al menos 1 vuelo."""
    return {
        "Falla_Radar": 0.60,
        "Inundacion": 0.30,
        "Falta_Combustible": 0.80,
        "Saturacion_Vial": 0.55,
        "Manga_Inoperativa": 0.70,
        "Otro": 0.20,
    }[tipo]


def _generar_incidencias(
    rng: random.Random,
    vuelos: list[dict],
    recursos: list[dict],
) -> None:
    """25k incidencias, IDs 1..25000 dentro del rango contractual 1..30000."""
    rucs_objetivo = {
        catalogos.AEROLINEAS[i][0]
        for i in config.AEROLINEAS_CON_MUCHO_COMBUSTIBLE_INDEX
    }
    vuelos_de_rucs_objetivo = [v for v in vuelos if v["ruc_aerolinea"] in rucs_objetivo]

    # Segregar recursos por tipo para elegir coherentemente
    recursos_mangas = [r["id"] for r in recursos if r["tipo"] == "manga"]
    recursos_radares = [r["id"] for r in recursos if r["tipo"] == "radar"]
    recursos_todos = [r["id"] for r in recursos]

    fecha_desde = datetime.fromisoformat(config.FECHA_DESDE).replace(tzinfo=timezone.utc)
    fecha_hasta = datetime.fromisoformat(config.FECHA_HASTA).replace(tzinfo=timezone.utc)
    segundos_totales = int((fecha_hasta - fecha_desde).total_seconds())

    def _iter():
        for id_incidencia in range(1, config.N_INCIDENCIAS + 1):
            tipo = _pick_weighted(rng, config.PCT_TIPO_INCIDENCIA)
            gravedad = _pick_weighted(rng, config.PCT_GRAVEDAD)

            # fecha_reporte uniforme en la ventana
            fecha_reporte = fecha_desde + timedelta(seconds=rng.randrange(segundos_totales))

            # fecha_cierre: NULL en PCT_INCIDENCIA_ABIERTA; sino +1..72 horas
            if rng.random() < config.PCT_INCIDENCIA_ABIERTA:
                fecha_cierre = None
            else:
                fecha_cierre = fecha_reporte + timedelta(hours=rng.randint(1, 72))

            # afecta_recursos[]: 1-3 recursos, coherentes con el tipo
            if tipo == "Falla_Radar":
                pool = recursos_radares
            elif tipo == "Manga_Inoperativa":
                pool = recursos_mangas
            else:
                pool = recursos_todos
            n_recursos = rng.randint(1, min(3, len(pool)))
            afecta_recursos = [{"recurso_id": rid} for rid in rng.sample(pool, k=n_recursos)]

            # retrasa_vuelos[]: probabilidad depende del tipo
            retrasa_vuelos = []
            if rng.random() < _pct_retrasa_vuelos_por_tipo(tipo):
                # Falta_Combustible SIEMPRE afecta a las aerolineas objetivo
                pool_vuelos = (
                    vuelos_de_rucs_objetivo if tipo == "Falta_Combustible" else vuelos
                )
                if pool_vuelos:
                    n_vuelos = rng.randint(1, min(5, len(pool_vuelos)))
                    retrasa_vuelos = [
                        {"vuelo_id": v["id"]}
                        for v in rng.sample(pool_vuelos, k=n_vuelos)
                    ]

            doc = {
                "id": id_incidencia,
                "gravedad": gravedad,
                "descripcion": _generar_descripcion(rng, tipo),
                "tipo_incidencia": tipo,
                "fecha_reporte": _iso_utc(fecha_reporte),
                "fecha_cierre": _iso_utc(fecha_cierre) if fecha_cierre else None,
                "afecta_recursos": afecta_recursos,
                "retrasa_vuelos": retrasa_vuelos,
            }
            yield doc

    n = _escribir_jsonl(config.OUTPUT_MS3 / "incidencias.jsonl", _iter())
    return n


# ---------------------------------------------------------------------------
# Colección: asignaciones (Utiliza — vuelo ↔ recurso)
# ---------------------------------------------------------------------------
def _generar_asignaciones(
    rng: random.Random,
    vuelos: list[dict],
    recursos: list[dict],
) -> int:
    """~40k pares únicos (vuelo, recurso). Cada vuelo tiene al menos 1 manga."""
    recursos_mangas = [r["id"] for r in recursos if r["tipo"] == "manga"]
    recursos_todos = [r["id"] for r in recursos]

    vistos: set[tuple[int, int]] = set()

    def _iter():
        # Fase 1: cada vuelo estrena con 1 manga asignada (regla del enunciado)
        for v in vuelos:
            manga_id = rng.choice(recursos_mangas)
            par = (v["id"], manga_id)
            if par not in vistos:
                vistos.add(par)
                yield {"vuelo_id": v["id"], "recurso_id": manga_id}

        # Fase 2: rellenar hasta N_ASIGNACIONES con pares aleatorios únicos
        intentos_max = config.N_ASIGNACIONES * 3
        while len(vistos) < config.N_ASIGNACIONES and intentos_max > 0:
            v = rng.choice(vuelos)
            rid = rng.choice(recursos_todos)
            par = (v["id"], rid)
            intentos_max -= 1
            if par in vistos:
                continue
            vistos.add(par)
            yield {"vuelo_id": v["id"], "recurso_id": rid}

    return _escribir_jsonl(config.OUTPUT_MS3 / "asignaciones.jsonl", _iter())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def generar(rng: random.Random, faker: Faker) -> dict:
    print("[MS3] leyendo pool de vuelos de MS2...")
    vuelos = _leer_vuelos_ms2()
    print(f"[MS3]   {len(vuelos)} vuelos leidos de MS2")

    print("[MS3] generando recursos (mangas + radares)...")
    recursos = _generar_recursos(rng)
    n_mangas = sum(1 for r in recursos if r["tipo"] == "manga")
    n_radares = sum(1 for r in recursos if r["tipo"] == "radar")
    print(f"[MS3]   {len(recursos)} recursos ({n_mangas} mangas + {n_radares} radares)")

    print("[MS3] generando incidencias...")
    _generar_incidencias(rng, vuelos, recursos)
    print(f"[MS3]   {config.N_INCIDENCIAS} incidencias")

    print("[MS3] generando asignaciones (vuelo <-> recurso)...")
    n_asignaciones = _generar_asignaciones(rng, vuelos, recursos)
    print(f"[MS3]   {n_asignaciones} asignaciones")

    return {}
