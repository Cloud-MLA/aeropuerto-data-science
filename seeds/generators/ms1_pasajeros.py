"""Generador de MS1 — Pasajeros / Tickets (MySQL).

Tablas producidas (CSV compatible con `LOAD DATA INFILE ... FIELDS TERMINATED BY ','
ENCLOSED BY '\"' LINES TERMINATED BY '\\n' IGNORE 1 LINES`):

    - categoria_migratoria (3, catálogo fijo)
    - persona              (60 000, IDs 100 000..159 999 — contrato §3)
    - pasajero             (60 000, 1:1 con persona vía IsA; UNIQUE(tipo_doc, num_doc))
    - ticket               (25 000, IDs 1..25 000 dentro del rango 1..60 000)
    - checkin              (~18 750, 75% de tickets)
    - equipaje             (~22 000, tag BHS##########; hereda id_persona/id_vuelo del ticket)

Depende de MS2: lee `output/ms2/vuelo.csv` para tener el pool de `vuelo_id`
+ `hora_programada` + `estado` (referencia suave — no hay FK física a MS2).
"""
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

import config
import catalogos


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _escribir_csv(ruta: Path, cabecera: list[str], filas) -> int:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(cabecera)
        for fila in filas:
            w.writerow(fila)
            n += 1
    return n


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_weighted(rng: random.Random, distribucion: dict[str, float]) -> str:
    valores = list(distribucion.keys())
    pesos = list(distribucion.values())
    return rng.choices(valores, weights=pesos, k=1)[0]


def _leer_vuelos_ms2() -> list[tuple[int, datetime, str]]:
    """Lee el pool de vuelos generado por MS2. Requiere que MS2 haya corrido antes.

    Retorna list de (id_vuelo, hora_programada UTC, estado).
    """
    ruta = config.OUTPUT_MS2 / "vuelo.csv"
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta}. Corre 'python generar.py --ms 2' primero."
        )
    vuelos = []
    with ruta.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for fila in r:
            vuelos.append((
                int(fila["id"]),
                datetime.strptime(fila["hora_programada"], "%Y-%m-%dT%H:%M:%SZ")
                    .replace(tzinfo=timezone.utc),
                fila["estado"],
            ))
    return vuelos


# ---------------------------------------------------------------------------
# Documentos de identidad
# ---------------------------------------------------------------------------
def _generar_documento(rng: random.Random, tipo: str) -> str:
    if tipo == "DNI":
        # 8 dígitos, primero != 0
        return f"{rng.randint(1, 9)}{rng.randint(0, 9999999):07d}"
    if tipo == "Pasaporte":
        # 2 letras + 7 dígitos
        letras = "".join(rng.choices("ABCDEFGHIJKLMNPQRSTUVWXYZ", k=2))
        return f"{letras}{rng.randint(0, 9999999):07d}"
    # Carnet de Extranjeria: 12 dígitos
    return f"{rng.randint(1, 9)}{rng.randint(0, 10**11 - 1):011d}"


# ---------------------------------------------------------------------------
# Tabla: categoria_migratoria
# ---------------------------------------------------------------------------
def _generar_categorias_migratorias() -> None:
    _escribir_csv(
        config.OUTPUT_MS1 / "categoria_migratoria.csv",
        ["id", "nombre", "tarifa"],
        ((id_, nombre, f"{tarifa:.2f}")
         for id_, nombre, tarifa in catalogos.CATEGORIAS_MIGRATORIAS),
    )


# ---------------------------------------------------------------------------
# Tabla: persona
# ---------------------------------------------------------------------------
def _generar_personas(rng: random.Random, faker: Faker) -> list[dict]:
    """Genera N_PERSONAS con IDs consecutivos en el rango contractual."""
    personas = []
    ids_rango = range(config.PERSONA_ID_MIN, config.PERSONA_ID_MIN + config.N_PERSONAS)
    for id_persona in ids_rango:
        personas.append({
            "id_persona": id_persona,
            "nombre": faker.first_name(),
            "apellido": faker.last_name(),
            "fecha_nacimiento": faker.date_of_birth(minimum_age=18, maximum_age=85).isoformat(),
        })
    _escribir_csv(
        config.OUTPUT_MS1 / "persona.csv",
        ["id_persona", "nombre", "apellido", "fecha_nacimiento"],
        ((p["id_persona"], p["nombre"], p["apellido"], p["fecha_nacimiento"]) for p in personas),
    )
    return personas


# ---------------------------------------------------------------------------
# Tabla: pasajero (IsA de persona)
# ---------------------------------------------------------------------------
def _generar_pasajeros(rng: random.Random, personas: list[dict]) -> list[dict]:
    """1:1 con persona. UNIQUE(tipo_documento, numero_documento) garantizado por
    la unicidad de la combinación en la generación (colisiones son teóricas y
    despreciables al volumen — 60k sobre 10^8 combinaciones DNI).
    """
    pasajeros = []
    documentos_vistos: set[tuple[str, str]] = set()
    id_por_nombre_categoria = {nombre: id_ for id_, nombre, _ in catalogos.CATEGORIAS_MIGRATORIAS}

    for persona in personas:
        # Muestreo con reintentos para garantizar unicidad
        for _ in range(10):
            tipo = _pick_weighted(rng, config.PCT_TIPO_DOCUMENTO)
            numero = _generar_documento(rng, tipo)
            if (tipo, numero) not in documentos_vistos:
                documentos_vistos.add((tipo, numero))
                break
        else:
            raise RuntimeError(f"No se pudo generar documento único para persona {persona['id_persona']}")

        nombre_categoria = _pick_weighted(rng, config.PCT_CATEGORIA_MIGRATORIA)
        id_categoria = id_por_nombre_categoria[nombre_categoria]
        pasajeros.append({
            "id_persona": persona["id_persona"],
            "tipo_documento": tipo,
            "numero_documento": numero,
            "id_categoria": id_categoria,
        })

    _escribir_csv(
        config.OUTPUT_MS1 / "pasajero.csv",
        ["id_persona", "tipo_documento", "numero_documento", "id_categoria"],
        ((p["id_persona"], p["tipo_documento"], p["numero_documento"], p["id_categoria"])
         for p in pasajeros),
    )
    return pasajeros


# ---------------------------------------------------------------------------
# Tabla: ticket
# ---------------------------------------------------------------------------
def _estado_boarding_para_vuelo(rng: random.Random, estado_vuelo: str) -> str:
    """Correlaciona estado_boarding del ticket con el estado del vuelo."""
    if estado_vuelo == "Cancelado":
        return "Cancelado"
    if estado_vuelo in ("Despegado", "Aterrizado"):
        return _pick_weighted(rng, {"Embarcado": 0.90, "No-show": 0.10})
    if estado_vuelo == "Embarcando":
        return _pick_weighted(rng, {"Check-in": 0.80, "Emitido": 0.20})
    if estado_vuelo == "Retrasado":
        return _pick_weighted(rng, {"Check-in": 0.60, "Embarcado": 0.30, "Emitido": 0.10})
    # Programado
    return _pick_weighted(rng, {"Emitido": 0.70, "Check-in": 0.30})


def _generar_tickets(
    rng: random.Random,
    personas: list[dict],
    vuelos_ms2: list[tuple[int, datetime, str]],
) -> list[dict]:
    """25k tickets con IDs 1..25000. id_vuelo e id_persona muestreados uniformemente."""
    tickets = []
    for id_ticket in range(1, config.N_TICKETS + 1):
        id_vuelo, hora_programada, estado_vuelo = rng.choice(vuelos_ms2)
        persona = rng.choice(personas)

        # fecha_emision: 1 a 90 días antes del vuelo (nunca en el futuro del vuelo)
        dias_antes = rng.randint(1, 90)
        fecha_emision = (hora_programada - timedelta(days=dias_antes)).date().isoformat()

        # Precio: distribución sesgada a rangos medios
        precio = round(rng.triangular(50, 800, 250), 2)

        tickets.append({
            "id_ticket": id_ticket,
            "precio": f"{precio:.2f}",
            "fecha_emision": fecha_emision,
            "estado_boarding": _estado_boarding_para_vuelo(rng, estado_vuelo),
            "id_vuelo": id_vuelo,
            "id_persona": persona["id_persona"],
            "_hora_programada": hora_programada,
        })

    _escribir_csv(
        config.OUTPUT_MS1 / "ticket.csv",
        ["id_ticket", "precio", "fecha_emision", "estado_boarding", "id_vuelo", "id_persona"],
        (
            (t["id_ticket"], t["precio"], t["fecha_emision"],
             t["estado_boarding"], t["id_vuelo"], t["id_persona"])
            for t in tickets
        ),
    )
    return tickets


# ---------------------------------------------------------------------------
# Tabla: checkin
# ---------------------------------------------------------------------------
def _generar_checkins(rng: random.Random, tickets: list[dict]) -> int:
    """~75% de tickets emitidos hace check-in. counter C01..C60, 80% con equipaje."""
    def _iter():
        for t in tickets:
            # No hacen check-in tickets cancelados o no-show, pero sí los demás con prob 75%
            if t["estado_boarding"] in ("Cancelado", "No-show", "Emitido"):
                continue  # esos son los que no llegaron al mostrador
            # Check-in / Embarcado sí hicieron
            minutos_antes = rng.randint(60, 240)
            fecha_hora = t["_hora_programada"] - timedelta(minutes=minutos_antes)
            counter = f"C{rng.randint(1, 60):02d}"
            con_equipaje = rng.random() < 0.80
            yield (
                t["id_ticket"],
                _iso_utc(fecha_hora),
                counter,
                "1" if con_equipaje else "0",  # MySQL BOOLEAN acepta 0/1
            )

    return _escribir_csv(
        config.OUTPUT_MS1 / "checkin.csv",
        ["id_ticket", "fecha_hora", "counter", "con_equipaje"],
        _iter(),
    )


# ---------------------------------------------------------------------------
# Tabla: equipaje
# ---------------------------------------------------------------------------
def _generar_equipajes(rng: random.Random, tickets: list[dict]) -> int:
    """Tag BHS + 10 dígitos. ~65% de tickets tiene equipaje; de esos, 70/30 tiene 1/2 maletas."""
    seq = 0

    def _iter():
        nonlocal seq
        for t in tickets:
            if t["estado_boarding"] in ("Cancelado", "No-show"):
                continue
            if rng.random() >= 0.75:
                continue  # 25% no factura equipaje
            n_maletas = 1 if rng.random() < 0.65 else 2
            for _ in range(n_maletas):
                seq += 1
                tag = f"BHS{seq:010d}"
                # Peso realista: log-normal recortada a 5-32 kg
                peso = round(min(32.0, max(5.0, rng.gauss(18, 6))), 2)
                yield (tag, f"{peso:.2f}", t["id_persona"], t["id_vuelo"])

    return _escribir_csv(
        config.OUTPUT_MS1 / "equipaje.csv",
        ["id", "peso", "id_persona", "id_vuelo"],
        _iter(),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def generar(rng: random.Random, faker: Faker) -> dict:
    print("[MS1] leyendo pool de vuelos de MS2...")
    vuelos_ms2 = _leer_vuelos_ms2()
    print(f"[MS1]   {len(vuelos_ms2)} vuelos leidos de MS2")

    print("[MS1] generando categoria_migratoria...")
    _generar_categorias_migratorias()
    print(f"[MS1]   {len(catalogos.CATEGORIAS_MIGRATORIAS)} categorias")

    print("[MS1] generando personas...")
    personas = _generar_personas(rng, faker)
    print(f"[MS1]   {len(personas)} personas")

    print("[MS1] generando pasajeros (IsA de persona)...")
    pasajeros = _generar_pasajeros(rng, personas)
    print(f"[MS1]   {len(pasajeros)} pasajeros")

    print("[MS1] generando tickets...")
    tickets = _generar_tickets(rng, personas, vuelos_ms2)
    print(f"[MS1]   {len(tickets)} tickets")

    print("[MS1] generando checkins...")
    n_checkins = _generar_checkins(rng, tickets)
    print(f"[MS1]   {n_checkins} checkins")

    print("[MS1] generando equipajes...")
    n_equipajes = _generar_equipajes(rng, tickets)
    print(f"[MS1]   {n_equipajes} equipajes")

    return {"pasajero_ids": [p["id_persona"] for p in pasajeros]}
