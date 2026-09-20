# E/R del catálogo del data lake (borrador para DS-13)

Borrador en **Mermaid** del E/R del catálogo Glue `aeropuerto_lake` — las 18 tablas que expone Athena tras la ingesta (DS-06/07/08). Sirve como referencia para que Alexander lo convierta a `.drawio` visual en `cloud-computing-proyecto/diagramas/er-catalogo-datalake.drawio` (DS-13, `hito2 §4`).

**Fuente de verdad de los schemas:** [`athena/local-postgres/schema.sql`](../athena/local-postgres/schema.sql). Aquí se muestran solo las claves — sin todos los atributos — para que el diagrama sea legible.

## Contexto — 3 schemas lógicos, 1 catálogo Glue

Cada microservicio pobla su prefijo en S3, y el crawler Glue lo indexa como tablas del catálogo `aeropuerto_lake`. Los join cross-schema son **referencias suaves** (sin FK física) porque en producción los MSs son procesos separados; en Athena todos viven en el mismo `SELECT ... JOIN ...`.

- **MS1** (MySQL en producción) → `raw/ms1/` → 6 tablas.
- **MS2** (PostgreSQL en producción) → `raw/ms2/` → 8 tablas.
- **MS3** (MongoDB en producción, aplanado por `ingesta-ms3`) → `raw/ms3/` → 5 tablas.

## Diagrama

```mermaid
erDiagram
    %% ============ MS1 (MySQL / raw/ms1/) ============
    persona {
        int id_persona PK
        string nombre
        string apellido
        date fecha_nacimiento
    }
    categoria_migratoria {
        int id PK
        string nombre "Nacional | Internacional | Transito"
        decimal tarifa "TUUA en soles"
    }
    pasajero {
        int id_persona PK_FK "IsA de persona"
        string tipo_documento "DNI | Pasaporte | Carnet"
        string numero_documento
        int id_categoria FK
    }
    ticket {
        int id_ticket PK
        decimal precio
        date fecha_emision
        string estado_boarding "Emitido | Check-in | Embarcado | No-show | Cancelado"
        int id_vuelo FK_soft "→ ms2.vuelo.id"
        int id_persona FK
    }
    checkin {
        int id_ticket PK_FK "1:1 con ticket"
        timestamp fecha_hora
        string counter
        boolean con_equipaje
    }
    equipaje {
        string id PK "BHS##########"
        decimal peso
        int id_persona FK
        int id_vuelo FK_soft "→ ms2.vuelo.id"
    }

    %% ============ MS2 (PostgreSQL / raw/ms2/) ============
    aerolinea {
        string ruc PK "11 digitos"
        string nombre
        string alianza "Star Alliance | SkyTeam | Oneworld | Ninguna"
    }
    aeronave {
        string placa PK "OB-####"
        string modelo
        string fabricante
        int capacidad
        string clase "A..F (OACI)"
    }
    asiento {
        string codigo PK
        string placa_aeronave PK_FK
    }
    empleado {
        int id PK
        string nombre
        string apellido
        date fecha_nacimiento
    }
    tripulacion {
        int id_empleado PK_FK "IsA de empleado"
        string num_licencia
    }
    operativo_tierra {
        int id_empleado PK_FK "IsA de empleado"
        string area_operativa
    }
    vuelo {
        int id PK
        string num_vuelo
        timestamp hora_programada
        timestamp hora_real "nullable"
        string estado "Programado | Embarcando | Despegado | Aterrizado | Retrasado | Cancelado"
        string tipo "Nacional | Internacional"
        string origen "IATA"
        string destino "IATA"
        string placa_aeronave FK
        string ruc_aerolinea FK
    }
    opera_tripulacion {
        int id_empleado PK_FK
        int id_vuelo PK_FK
    }

    %% ============ MS3 (MongoDB aplanado / raw/ms3/) ============
    recurso {
        int id PK
        string nombre_tecnico_locacion
        string tipo "manga | radar"
        string estado_acople "nullable, solo manga"
        decimal longitud "nullable, solo manga"
        string clase_max "nullable, solo manga"
        int rango_alcance "nullable, solo radar"
        string frecuencia "nullable, solo radar"
    }
    incidencia {
        int id PK
        string gravedad "Leve | Moderada | Alta | Critica"
        string descripcion
        string tipo_incidencia "Falla_Radar | Falta_Combustible | ..."
        timestamp fecha_reporte
        timestamp fecha_cierre "nullable"
    }
    incidencia_afecta_recurso {
        int id_incidencia PK_FK
        int id_recurso PK_FK
    }
    incidencia_retrasa_vuelo {
        int id_incidencia PK_FK
        int id_vuelo PK_FK_soft "→ ms2.vuelo.id"
    }
    asignacion {
        int id_vuelo PK_FK_soft "→ ms2.vuelo.id"
        int id_recurso PK_FK
    }

    %% ============ RELACIONES INTRA-SCHEMA ============
    persona ||--|| pasajero : IsA
    categoria_migratoria ||--o{ pasajero : "clasifica"
    pasajero ||--o{ ticket : "compra"
    pasajero ||--o{ equipaje : "factura"
    ticket ||--|| checkin : "genera"

    aerolinea ||--o{ vuelo : "opera"
    aeronave ||--o{ vuelo : "asigna"
    aeronave ||--o{ asiento : "contiene"
    empleado ||--o| tripulacion : IsA
    empleado ||--o| operativo_tierra : IsA
    tripulacion ||--o{ opera_tripulacion : "asignada a"
    vuelo ||--o{ opera_tripulacion : "atendido por"

    recurso ||--o{ incidencia_afecta_recurso : "afectado por"
    incidencia ||--o{ incidencia_afecta_recurso : "afecta"
    incidencia ||--o{ incidencia_retrasa_vuelo : "retrasa"
    recurso ||--o{ asignacion : "usado en"

    %% ============ RELACIONES CROSS-SCHEMA (soft, sin FK física) ============
    vuelo ||..o{ ticket : "ms1↔ms2 (soft)"
    vuelo ||..o{ equipaje : "ms1↔ms2 (soft)"
    vuelo ||..o{ incidencia_retrasa_vuelo : "ms2↔ms3 (soft)"
    vuelo ||..o{ asignacion : "ms2↔ms3 (soft)"
```

## Claves de join que usan las 5 queries Q1–Q5

| Query | Join | Tablas |
|---|---|---|
| **Q1** — recursos con más incidencias | `incidencia_afecta_recurso.id_incidencia ↔ incidencia.id`; `.id_recurso ↔ recurso.id` | 3 (todas MS3) |
| **Q2** — retraso promedio por tipo | `vuelo` sola (agrega por `tipo` y franja horaria) | 1 (MS2) |
| **Q3** — Falta_Combustible por aerolínea | `incidencia_retrasa_vuelo.id_vuelo ↔ vuelo.id` (**cross-schema**); `vuelo.ruc_aerolinea ↔ aerolinea.ruc` | 4 (MS2+MS3) |
| **Q4** — recaudación TUUA por categoría | `ticket.id_persona ↔ pasajero.id_persona`; `pasajero.id_categoria ↔ categoria_migratoria.id`; `ticket.id_vuelo ↔ vuelo.id` (**cross-schema**) | 4 (MS1+MS2) |
| **Q5** — % hora punta retrasados | `vuelo` sola | 1 (MS2) |

Las 3 queries que hacen cross-schema son Q3 (MS2 × MS3) y Q4 (MS1 × MS2). Sin catálogo unificado en Athena, cada MS quedaría aislado — el catálogo Glue es lo que permite `JOIN` entre tablas de motores distintos.

## Notas para Alexander (para pasarlo a `.drawio`)

1. **Agrupa visualmente por schema** (MS1 arriba, MS2 al centro, MS3 abajo) con un rectángulo/fondo distinto para cada uno. Los MSs son sistemas separados en producción — el diagrama debe transmitir eso.
2. **Diferencia relaciones "hard" (línea sólida) de "soft" (línea punteada)** — Mermaid ya usa `||..o{` (punteado) para las cross-schema y `||--o{` (sólido) para las intra-schema.
3. **Destaca las 4 líneas cross-schema con color** (rojo/amarillo). Son las que Athena tiene que resolver y no se ven en el schema físico de ninguna BD.
4. **Marca las 5 tablas "clave" de negocio** (vuelo, ticket, incidencia, pasajero, aerolinea) con un fondo distinto — son las que salen en las 5 queries.
5. **En el título del diagrama** poner: `Catálogo aeropuerto_lake (Glue) — 18 tablas · 3 fuentes MS1/MS2/MS3`.

## Cómo previsualizar el Mermaid antes de convertir

- **VS Code:** extensión "Markdown Preview Mermaid Support" — ver este archivo con `Ctrl+Shift+V`.
- **Online:** pegar el bloque `mermaid` en https://mermaid.live y descargar como PNG/SVG para bocetar sobre `.drawio`.
- **draw.io directo:** File → Import from → Mermaid... (funciona con la sintaxis `erDiagram`).

Cuando el `.drawio` esté listo, sube el archivo (+ PNG exportado) a `cloud-computing-proyecto/diagramas/er-catalogo-datalake.drawio` y marca DS-13 como ☑ en `docs/plan/personas/fabricio.md`.
