"""Generador de MS2 — Vuelos / Operaciones (PostgreSQL).

Tablas producidas (CSV compatible con `\\COPY ... CSV HEADER`):
    - aerolinea          (24 filas del catálogo real)
    - aeronave           (~150 filas, flota realista para 24 aerolíneas)
    - asiento            (~30 000, entidad débil de aeronave)
    - empleado           (5 000, con nombre/apellido/fecha_nacimiento embebidos)
    - tripulacion        (~3 000, subclase IsA de empleado, con num_licencia)
    - operativo_tierra   (~2 000, subclase IsA de empleado, con area_operativa)
    - vuelo              (25 000, tabla de volumen ≥20k)
    - opera_tripulacion  (~100 000, relación N–M vuelo ↔ tripulante)

Se ejecuta primero en el orden MS2 → MS1 → MS3 porque MS1 y MS3 muestrean
`vuelo.id` del pool aquí generado (contrato §3 del plan-de-trabajo).
"""
import csv
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

import config
import catalogos


# Códigos IATA de 2 caracteres por aerolínea, indexados por posición en catalogos.AEROLINEAS.
# Sirven para construir `num_vuelo` en formato "LA2477".
_IATA_POR_INDICE = [
    "LA", "H2", "JA", "2I", "AV", "CM", "AC", "UA",
    "AM", "AF", "KL", "DL", "AR", "IB", "AA", "BA",
    "LV", "G3", "OB", "P5", "ET", "LH", "UX", "QR",
]


def _pick_weighted(rng: random.Random, distribucion: dict[str, float]) -> str:
    """Muestreo por pesos; devuelve una clave según sus probabilidades."""
    valores = list(distribucion.keys())
    pesos = list(distribucion.values())
    return rng.choices(valores, weights=pesos, k=1)[0]


def _iso_utc(dt: datetime) -> str:
    """ISO 8601 UTC compacto: '2026-08-15T14:22:00Z' (contrato de enums.md)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _escribir_csv(ruta: Path, cabecera: list[str], filas) -> int:
    """Escribe filas a un CSV con header. Devuelve la cantidad escrita."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(cabecera)
        for fila in filas:
            w.writerow(fila)
            n += 1
    return n


# ---------------------------------------------------------------------------
# Tabla: aerolinea
# ---------------------------------------------------------------------------
def _generar_aerolineas() -> list[dict]:
    """Toma el catálogo fijo — sin aleatoriedad."""
    aerolineas = []
    for i, (ruc, nombre, alianza) in enumerate(catalogos.AEROLINEAS):
        aerolineas.append({
            "ruc": ruc,
            "nombre": nombre,
            "alianza": alianza,
            "_iata": _IATA_POR_INDICE[i],
        })
    ruta = config.OUTPUT_MS2 / "aerolinea.csv"
    _escribir_csv(
        ruta,
        ["ruc", "nombre", "alianza"],
        ((a["ruc"], a["nombre"], a["alianza"]) for a in aerolineas),
    )
    return aerolineas


# ---------------------------------------------------------------------------
# Tabla: aeronave
# ---------------------------------------------------------------------------
def _generar_aeronaves(rng: random.Random) -> list[dict]:
    """Genera N_AERONAVES con placa OB-#### y modelo tomado del catálogo real."""
    aeronaves = []
    for i in range(config.N_AERONAVES):
        placa = f"OB-{1000 + i:04d}"
        modelo, fabricante, capacidad, clase = rng.choice(catalogos.MODELOS_AERONAVE)
        aeronaves.append({
            "placa": placa,
            "modelo": modelo,
            "fabricante": fabricante,
            "capacidad": capacidad,
            "clase": clase,
        })
    ruta = config.OUTPUT_MS2 / "aeronave.csv"
    _escribir_csv(
        ruta,
        ["placa", "modelo", "fabricante", "capacidad", "clase"],
        ((a["placa"], a["modelo"], a["fabricante"], a["capacidad"], a["clase"]) for a in aeronaves),
    )
    return aeronaves


# ---------------------------------------------------------------------------
# Tabla: asiento (entidad débil de aeronave)
# ---------------------------------------------------------------------------
def _generar_asientos(aeronaves: list[dict]) -> int:
    """Por cada aeronave genera `capacidad` asientos en filas de 6 (A–F)."""
    ruta = config.OUTPUT_MS2 / "asiento.csv"

    def _iter():
        letras = ["A", "B", "C", "D", "E", "F"]
        for aeronave in aeronaves:
            capacidad = aeronave["capacidad"]
            # ceil(capacidad / 6) filas de 6 asientos
            fila = 1
            emitidos = 0
            while emitidos < capacidad:
                for letra in letras:
                    if emitidos >= capacidad:
                        break
                    codigo = f"{fila}{letra}"
                    yield (codigo, aeronave["placa"])
                    emitidos += 1
                fila += 1

    return _escribir_csv(ruta, ["codigo", "placa_aeronave"], _iter())


# ---------------------------------------------------------------------------
# Tabla: empleado + subclases tripulacion / operativo_tierra
# ---------------------------------------------------------------------------
def _generar_empleados_y_subclases(
    rng: random.Random, faker: Faker
) -> tuple[list[dict], list[int], list[int]]:
    """Empleado + tripulacion + operativo_tierra (IsA, tabla por subclase).

    Retorna (empleados, ids_tripulacion, ids_operativo_tierra).
    """
    empleados = []
    n_tripulantes = int(config.N_EMPLEADOS * config.PCT_EMPLEADOS_TRIPULACION)
    ids_tripulacion: list[int] = []
    ids_operativo: list[int] = []

    for id_empleado in range(1, config.N_EMPLEADOS + 1):
        empleado = {
            "id": id_empleado,
            "nombre": faker.first_name(),
            "apellido": faker.last_name(),
            "fecha_nacimiento": faker.date_of_birth(minimum_age=22, maximum_age=60).isoformat(),
        }
        empleados.append(empleado)
        if id_empleado <= n_tripulantes:
            ids_tripulacion.append(id_empleado)
        else:
            ids_operativo.append(id_empleado)

    # empleado.csv
    _escribir_csv(
        config.OUTPUT_MS2 / "empleado.csv",
        ["id", "nombre", "apellido", "fecha_nacimiento"],
        ((e["id"], e["nombre"], e["apellido"], e["fecha_nacimiento"]) for e in empleados),
    )

    # tripulacion.csv (id_empleado, num_licencia UNIQUE emitida por DGAC)
    _escribir_csv(
        config.OUTPUT_MS2 / "tripulacion.csv",
        ["id_empleado", "num_licencia"],
        ((tid, f"DGAC-{tid:06d}") for tid in ids_tripulacion),
    )

    # operativo_tierra.csv (id_empleado, area_operativa)
    _escribir_csv(
        config.OUTPUT_MS2 / "operativo_tierra.csv",
        ["id_empleado", "area_operativa"],
        ((oid, rng.choice(catalogos.AREAS_OPERATIVAS)) for oid in ids_operativo),
    )

    return empleados, ids_tripulacion, ids_operativo


# ---------------------------------------------------------------------------
# Tabla: vuelo
# ---------------------------------------------------------------------------
def _generar_vuelos(
    rng: random.Random, aerolineas: list[dict], aeronaves: list[dict]
) -> list[dict]:
    """Genera N_VUELOS con id 1..N, distribuidos en la ventana temporal.

    - `tipo` se deriva del destino (LIM ↔ nacional | internacional).
    - `hora_programada` sesgada a horas pico (PCT_VUELOS_EN_HORA_PICO).
    - `hora_real` es NULL si estado ∈ {Programado, Embarcando, Cancelado}.
    - Aerolíneas 0 y 5 reciben más vuelos → habilita ranking claro en Q3.
    """
    fecha_desde = date.fromisoformat(config.FECHA_DESDE)
    fecha_hasta = date.fromisoformat(config.FECHA_HASTA)
    dias_totales = (fecha_hasta - fecha_desde).days + 1

    # Pesos de aerolínea: 2 con más vuelos, resto uniforme
    pesos_aerolinea = [1.0] * len(aerolineas)
    for idx in config.AEROLINEAS_CON_MUCHO_COMBUSTIBLE_INDEX:
        pesos_aerolinea[idx] = 3.0

    contadores_por_aerolinea: dict[str, int] = {a["ruc"]: 0 for a in aerolineas}
    vuelos = []

    for id_vuelo in range(1, config.N_VUELOS + 1):
        aerolinea = rng.choices(aerolineas, weights=pesos_aerolinea, k=1)[0]
        aeronave = rng.choice(aeronaves)

        # num_vuelo: "LA2477" (IATA + secuencia por aerolínea)
        contadores_por_aerolinea[aerolinea["ruc"]] += 1
        num_vuelo = f"{aerolinea['_iata']}{contadores_por_aerolinea[aerolinea['ruc']]:04d}"

        # origen/destino: 50% salidas desde LIM, 50% llegadas a LIM
        if rng.random() < 0.5:
            origen = catalogos.IATA_ORIGEN
            destino = rng.choice(
                catalogos.IATAS_DESTINO_NACIONAL + catalogos.IATAS_DESTINO_INTERNACIONAL
            )
        else:
            destino = catalogos.IATA_ORIGEN
            origen = rng.choice(
                catalogos.IATAS_DESTINO_NACIONAL + catalogos.IATAS_DESTINO_INTERNACIONAL
            )

        # tipo derivado del destino no-LIM
        no_lim = destino if origen == catalogos.IATA_ORIGEN else origen
        tipo = "Nacional" if no_lim in catalogos.IATAS_DESTINO_NACIONAL else "Internacional"

        # hora_programada: sesgada a horas pico
        dia_offset = rng.randrange(dias_totales)
        fecha_base = fecha_desde + timedelta(days=dia_offset)
        if rng.random() < config.PCT_VUELOS_EN_HORA_PICO:
            hora = rng.choice(config.HORAS_PICO)
        else:
            hora = rng.randrange(24)
        minuto = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
        hora_programada = datetime(
            fecha_base.year, fecha_base.month, fecha_base.day,
            hora, minuto, tzinfo=timezone.utc,
        )

        estado = _pick_weighted(rng, config.PCT_ESTADO_VUELO)
        if estado in ("Programado", "Embarcando", "Cancelado"):
            hora_real = None
        elif estado == "Retrasado":
            hora_real = hora_programada + timedelta(minutes=rng.randint(16, 120))
        else:  # Despegado / Aterrizado
            hora_real = hora_programada + timedelta(minutes=rng.randint(0, 30))

        vuelos.append({
            "id": id_vuelo,
            "num_vuelo": num_vuelo,
            "hora_programada": hora_programada,
            "hora_real": hora_real,
            "estado": estado,
            "tipo": tipo,
            "origen": origen,
            "destino": destino,
            "placa_aeronave": aeronave["placa"],
            "ruc_aerolinea": aerolinea["ruc"],
        })

    ruta = config.OUTPUT_MS2 / "vuelo.csv"
    _escribir_csv(
        ruta,
        ["id", "num_vuelo", "hora_programada", "hora_real",
         "estado", "tipo", "origen", "destino", "placa_aeronave", "ruc_aerolinea"],
        (
            (
                v["id"], v["num_vuelo"],
                _iso_utc(v["hora_programada"]),
                _iso_utc(v["hora_real"]) if v["hora_real"] is not None else "",
                v["estado"], v["tipo"], v["origen"], v["destino"],
                v["placa_aeronave"], v["ruc_aerolinea"],
            )
            for v in vuelos
        ),
    )
    return vuelos


# ---------------------------------------------------------------------------
# Tabla: opera_tripulacion (N–M)
# ---------------------------------------------------------------------------
def _generar_opera_tripulacion(
    rng: random.Random, ids_tripulacion: list[int], vuelos: list[dict]
) -> int:
    """Por cada vuelo asigna 3–6 tripulantes distintos. PK = (id_empleado, id_vuelo)."""
    ruta = config.OUTPUT_MS2 / "opera_tripulacion.csv"
    n_tripulantes = len(ids_tripulacion)

    def _iter():
        for vuelo in vuelos:
            k = rng.randint(3, min(6, n_tripulantes))
            for id_emp in rng.sample(ids_tripulacion, k=k):
                yield (id_emp, vuelo["id"])

    return _escribir_csv(ruta, ["id_empleado", "id_vuelo"], _iter())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def generar(rng: random.Random, faker: Faker) -> dict:
    """Genera todos los CSV de MS2. Retorna referencias reusables por MS1/MS3.

    Returns:
        {
            "vuelo_ids": list[int],       # para MS1 (tickets/equipaje) y MS3 (asignaciones)
            "aerolinea_rucs": list[str],  # por si algún otro MS lo necesita
        }
    """
    print("[MS2] generando aerolineas...")
    aerolineas = _generar_aerolineas()
    print(f"[MS2]   {len(aerolineas)} aerolineas")

    print("[MS2] generando aeronaves...")
    aeronaves = _generar_aeronaves(rng)
    print(f"[MS2]   {len(aeronaves)} aeronaves")

    print("[MS2] generando asientos...")
    n_asientos = _generar_asientos(aeronaves)
    print(f"[MS2]   {n_asientos} asientos")

    print("[MS2] generando empleados + tripulacion + operativo_tierra...")
    empleados, ids_tripulacion, ids_operativo = _generar_empleados_y_subclases(rng, faker)
    print(f"[MS2]   {len(empleados)} empleados "
          f"({len(ids_tripulacion)} tripulacion + {len(ids_operativo)} operativo_tierra)")

    print("[MS2] generando vuelos...")
    vuelos = _generar_vuelos(rng, aerolineas, aeronaves)
    print(f"[MS2]   {len(vuelos)} vuelos")

    print("[MS2] generando opera_tripulacion (N-M)...")
    n_opera = _generar_opera_tripulacion(rng, ids_tripulacion, vuelos)
    print(f"[MS2]   {n_opera} pares opera_tripulacion")

    return {
        "vuelo_ids": [v["id"] for v in vuelos],
        "aerolinea_rucs": [a["ruc"] for a in aerolineas],
    }
