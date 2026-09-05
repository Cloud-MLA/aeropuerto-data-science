# seeds/ — Generador de data ficticia compartido

Genera **CSVs (MS1/MS2) y JSONL (MS3)** con IDs deterministas que cruzan entre los 3 microservicios, para que la carga de 20 000+ registros por BD y los `JOIN` de Athena funcionen.

Referencia: [`plan-de-trabajo.md §3`](https://github.com/btoroled/cloud-computing-proyecto/blob/main/docs/plan-de-trabajo.md) y [`contratos/enums.md`](https://github.com/btoroled/cloud-computing-proyecto/blob/main/docs/contratos/enums.md).

---

## Cómo correrlo

```bash
cd seeds
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux
pip install -r requirements.txt

python generar.py           # genera todo en output/
python generar.py --ms 2    # solo MS2
python generar.py --ms 1    # solo MS1 (requiere haber corrido MS2 antes)
python generar.py --ms 3    # solo MS3
```

Salida en `output/`:

```
output/
├── ms1/
│   ├── persona.csv
│   ├── categoria_migratoria.csv
│   ├── pasajero.csv
│   ├── ticket.csv
│   ├── checkin.csv
│   └── equipaje.csv
├── ms2/
│   ├── aerolinea.csv
│   ├── aeronave.csv
│   ├── asiento.csv
│   ├── empleado.csv
│   ├── tripulacion.csv
│   ├── operativo_tierra.csv
│   ├── vuelo.csv
│   └── opera_tripulacion.csv
└── ms3/
    ├── recursos.jsonl
    ├── incidencias.jsonl
    └── asignaciones.jsonl
```

Con el mismo `SEED` (fijo en `config.py`), la salida es **byte a byte reproducible**.

---

## Cómo cargar los datos en cada BD

### MS1 — MySQL (Dev A)

```sql
LOAD DATA LOCAL INFILE 'output/ms1/persona.csv'
INTO TABLE persona
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES;
-- repetir por cada tabla en el orden: persona, categoria_migratoria, pasajero, ticket, checkin, equipaje
```

### MS2 — PostgreSQL (Dev B)

```sql
\COPY aerolinea FROM 'output/ms2/aerolinea.csv' CSV HEADER;
\COPY aeronave FROM 'output/ms2/aeronave.csv' CSV HEADER;
\COPY asiento FROM 'output/ms2/asiento.csv' CSV HEADER;
\COPY empleado FROM 'output/ms2/empleado.csv' CSV HEADER;
\COPY tripulacion FROM 'output/ms2/tripulacion.csv' CSV HEADER;
\COPY operativo_tierra FROM 'output/ms2/operativo_tierra.csv' CSV HEADER;
\COPY vuelo FROM 'output/ms2/vuelo.csv' CSV HEADER;
\COPY opera_tripulacion FROM 'output/ms2/opera_tripulacion.csv' CSV HEADER;
```

### MS3 — MongoDB (Dev C)

```bash
mongoimport --db infra_db --collection recursos     --file output/ms3/recursos.jsonl
mongoimport --db infra_db --collection incidencias  --file output/ms3/incidencias.jsonl
mongoimport --db infra_db --collection asignaciones --file output/ms3/asignaciones.jsonl
```

---

## Rangos de ID (contrato del líder)

| Entidad | Rango | Volumen que genero |
|---|---|---|
| `vuelo.id` | 1 – 25 000 | 25 000 |
| `aerolinea.ruc` | 11 dígitos (RUCs reales del PDF de BD1) | 24 |
| `aeronave.placa` | `OB-####` | 1 000 |
| `persona.id` / `pasajero.id` | 100 000 – 160 000 | 60 000 |
| `ticket.id` | 1 – 60 000 | 25 000 |
| `recurso.id` | 1 – 500 | 500 (350 mangas + 150 radares) |
| `incidencia.id` | 1 – 30 000 | 25 000 |

Tablas de volumen ≥20 000 (requisito de rúbrica): `ticket`, `equipaje` (MS1) · `vuelo`, `asiento` (MS2) · `incidencias` (MS3). Todas superadas.

---

## Orden de generación

**MS2 → MS1 → MS3.** Los IDs de vuelo salen de MS2; MS1 y MS3 los muestrean del set generado. Cambiar el orden rompe los joins.
