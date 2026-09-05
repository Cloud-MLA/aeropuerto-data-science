"""Catálogos con datos reales (no aleatorios) extraídos del PDF de BD1
y de los contratos de enums.md.

Estos valores son fijos entre corridas — no dependen del SEED.
"""

# 24 aerolíneas reales del PDF de BD1, con su alianza global.
# Los RUCs son sintéticos (información tributaria reservada) pero el formato es real.
AEROLINEAS = [
    ("20100000001", "LATAM Airlines Peru", "Ninguna"),
    ("20100000002", "Sky Airline Peru", "Ninguna"),
    ("20100000003", "JetSMART", "Ninguna"),
    ("20100000004", "Star Peru", "Ninguna"),
    ("20100000005", "Avianca", "Star Alliance"),
    ("20100000006", "Copa Airlines", "Star Alliance"),
    ("20100000007", "Air Canada", "Star Alliance"),
    ("20100000008", "United Airlines", "Star Alliance"),
    ("20100000009", "Aeromexico", "SkyTeam"),
    ("20100000010", "Air France", "SkyTeam"),
    ("20100000011", "KLM Royal Dutch Airlines", "SkyTeam"),
    ("20100000012", "Delta Air Lines", "SkyTeam"),
    ("20100000013", "Aerolineas Argentinas", "SkyTeam"),
    ("20100000014", "Iberia", "Oneworld"),
    ("20100000015", "American Airlines", "Oneworld"),
    ("20100000016", "British Airways", "Oneworld"),
    ("20100000017", "LEVEL", "Ninguna"),
    ("20100000018", "GOL", "Ninguna"),
    ("20100000019", "Boliviana de Aviacion", "Ninguna"),
    ("20100000020", "Wingo", "Ninguna"),
    ("20100000021", "Ethiopian Airlines", "Star Alliance"),
    ("20100000022", "Lufthansa", "Star Alliance"),
    ("20100000023", "Air Europa", "SkyTeam"),
    ("20100000024", "Qatar Airways", "Oneworld"),
]

# Modelos reales que operan en LIM (Aeropuerto Jorge Chávez).
# Cada tupla: (modelo, fabricante, capacidad, clase OACI)
MODELOS_AERONAVE = [
    ("A320neo", "Airbus", 180, "C"),
    ("A321neo", "Airbus", 220, "C"),
    ("A319", "Airbus", 150, "C"),
    ("A350-900", "Airbus", 325, "E"),
    ("A330-200", "Airbus", 280, "E"),
    ("Boeing 787-9", "Boeing", 296, "E"),
    ("Boeing 777-300ER", "Boeing", 396, "E"),
    ("Boeing 737-800", "Boeing", 189, "C"),
    ("Boeing 737 MAX 8", "Boeing", 210, "C"),
    ("Boeing 767-300", "Boeing", 269, "D"),
    ("Embraer E190", "Embraer", 100, "B"),
    ("Embraer E195-E2", "Embraer", 132, "B"),
    ("ATR 72-600", "ATR", 78, "A"),
]

# Categorías migratorias oficiales (tarifa TUUA en soles).
CATEGORIAS_MIGRATORIAS = [
    (1, "Nacional", 12.50),
    (2, "Internacional", 38.45),
    (3, "Transito", 18.00),
]

# Aeropuertos de origen/destino frecuentes en LIM (código IATA).
IATAS_DESTINO_NACIONAL = ["CUZ", "AQP", "TRU", "IQT", "PIU", "TCQ", "TPP", "AYP", "JUL", "CIX"]
IATAS_DESTINO_INTERNACIONAL = [
    "SCL", "EZE", "BOG", "GRU", "MIA", "MAD", "MEX", "PTY",
    "JFK", "LAX", "AMS", "CDG", "DOH", "GIG", "SDQ", "UIO",
]
IATA_ORIGEN = "LIM"  # todos parten o llegan a LIM

# Frecuencias de radar oficiales.
FRECUENCIAS_RADAR = ["Banda L", "Banda S", "Banda C", "Banda X"]

# Áreas operativas para operativo_tierra.
AREAS_OPERATIVAS = ["Rampa", "Equipajes", "Seguridad", "Mantenimiento", "Plataforma"]

# Tipos de documento.
TIPOS_DOCUMENTO = ["DNI", "Pasaporte", "Carnet de Extranjeria"]

# Clases OACI en orden (A < B < C < D < E < F) para validar manga vs aeronave.
CLASES_OACI = ["A", "B", "C", "D", "E", "F"]

# Nombres técnicos de locación para recursos (patrón realista del aeropuerto).
def nombre_manga(i: int) -> str:
    espigon = ["A", "B", "C", "D", "E"][i % 5]
    puente = f"{espigon}{(i // 5) % 30 + 1:02d}"
    return f"Espigon {espigon} - Puente {puente}"


def nombre_radar(i: int) -> str:
    zona = ["Norte", "Sur", "Este", "Oeste", "Central"][i % 5]
    return f"Radar {zona} - Torre {i // 5 + 1:02d}"
