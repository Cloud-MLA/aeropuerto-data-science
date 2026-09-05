"""Configuración global del generador de seeds.

Todos los rangos y volúmenes están fijos aquí para que el output sea
reproducible byte-a-byte con el mismo SEED.

Referencia: docs/plan-de-trabajo.md §3 del repo cloud-computing-proyecto.
"""
from pathlib import Path

SEED = 20260905

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_MS1 = OUTPUT_DIR / "ms1"
OUTPUT_MS2 = OUTPUT_DIR / "ms2"
OUTPUT_MS3 = OUTPUT_DIR / "ms3"

# ---------- Rangos de ID (contrato compartido) ----------
VUELO_ID_MIN, VUELO_ID_MAX = 1, 25_000
PERSONA_ID_MIN, PERSONA_ID_MAX = 100_000, 160_000
TICKET_ID_MIN, TICKET_ID_MAX = 1, 60_000
RECURSO_ID_MIN, RECURSO_ID_MAX = 1, 500
INCIDENCIA_ID_MIN, INCIDENCIA_ID_MAX = 1, 30_000

# ---------- Volúmenes a generar ----------
N_AEROLINEAS = 24              # catálogo real del PDF de BD1
N_AERONAVES = 150              # flota realista para 24 aerolíneas
                               # → ~30k asientos totales (≥20k para MS2) ✅
N_EMPLEADOS = 5_000            # 60% tripulacion, 40% operativo_tierra
PCT_EMPLEADOS_TRIPULACION = 0.60
N_VUELOS = 25_000              # ≥20k para MS2
TRIPULANTES_POR_VUELO_PROMEDIO = 4   # → ~100k opera_tripulacion (N–M)

N_PERSONAS = 60_000
N_PASAJEROS = 60_000           # 1:1 con persona (jerarquía IsA)
N_TICKETS = 25_000             # ≥20k para MS1
N_CHECKINS_PCT = 0.72          # ~72% de tickets hacen check-in
N_EQUIPAJES = 22_000           # ≥20k para MS1

N_RECURSOS_MANGAS = 350
N_RECURSOS_RADARES = 150
N_INCIDENCIAS = 25_000         # ≥20k para MS3
N_ASIGNACIONES = 40_000        # vuelo ↔ recurso

# ---------- Distribuciones de negocio ----------
PCT_CATEGORIA_MIGRATORIA = {"Nacional": 0.60, "Internacional": 0.35, "Transito": 0.05}
PCT_ESTADO_VUELO = {
    "Programado": 0.30,
    "Embarcando": 0.05,
    "Despegado": 0.10,
    "Aterrizado": 0.35,
    "Retrasado": 0.15,
    "Cancelado": 0.05,
}
PCT_TIPO_INCIDENCIA = {
    "Falla_Radar": 0.15,
    "Inundacion": 0.05,
    "Falta_Combustible": 0.20,
    "Saturacion_Vial": 0.25,
    "Manga_Inoperativa": 0.30,
    "Otro": 0.05,
}
PCT_GRAVEDAD = {"Leve": 0.40, "Moderada": 0.35, "Alta": 0.20, "Critica": 0.05}
PCT_INCIDENCIA_ABIERTA = 0.30   # sin fecha_cierre

# Horas pico para que la query Q5 tenga señal
HORAS_PICO = [6, 7, 8, 18, 19, 20]
PCT_VUELOS_EN_HORA_PICO = 0.55

# Sesgar Falta_Combustible a estas aerolíneas (índices en el catálogo real)
# para que Q3 tenga un ranking claro
AEROLINEAS_CON_MUCHO_COMBUSTIBLE_INDEX = [0, 5]

# Ventana temporal de los datos
FECHA_DESDE = "2026-08-01"
FECHA_HASTA = "2026-09-30"
