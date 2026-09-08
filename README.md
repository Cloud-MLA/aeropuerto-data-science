# aeropuerto-data-science

Componente **Data Science / Analytics** del proyecto CS2032 — Cloud Computing (Ciclo 2026-2).
Dominio: **Aeropuerto Internacional Jorge Chávez**.

Este repo cubre el pipeline de datos que alimenta al microservicio analítico **MS5**:

```
seeds/  →  MS1/MS2/MS3 (cargan 20k+ en sus BD)  →  ingesta/  →  S3  →  Glue  →  Athena  →  MS5
```

---

## Contenido

| Carpeta | Qué es | Responsable |
|---|---|---|
| `seeds/` | Generador Python de data ficticia con `SEED` fijo. Produce CSV/JSONL cruzables entre MS1, MS2 y MS3. Guillermo, Mariano y Edinson lo usan para cargar sus 20k+ registros. | Fabricio |
| `ingesta/` | 3 contenedores Docker de ingesta (uno por microservicio con BD). Estrategia **pull del 100%**: leen la BD entera y suben archivos a S3. | `ingesta-ms1` Guillermo · `ingesta-ms2` Mariano · `ingesta-ms3` Edinson |
| `glue/` | Scripts y DDL para crear la base `aeropuerto_lake` y los crawlers en AWS Glue. | Fabricio |
| `athena/` | Las 5 consultas SQL (Q1–Q5) + las 2 vistas (`vw_recaudacion_tuua`, `vw_retrasos_hora_punta`). | Fabricio |

---

## Cumplimiento de la rúbrica de Data Science (5 pts)

Del [enunciado del proyecto](https://github.com/btoroled/cloud-computing-proyecto/blob/main/docs/requerimientos.md#47-data-science--repo-aeropuerto-data-science):

- [ ] Bucket S3 `s3://<equipo>-aeropuerto-lake/` con prefijos `raw/ms1/`, `raw/ms2/`, `raw/ms3/`.
- [ ] 3 contenedores Docker Python con estrategia **pull del 100%**.
- [ ] Catálogo AWS Glue (`aeropuerto_lake`) con una tabla por archivo cargado.
- [ ] Diagrama E/R del catálogo (`diagramas/er-catalogo-datalake.drawio` en el repo de docs).
- [ ] ≥4 consultas Athena con `JOIN` entre tablas de ms1 + ms2 + ms3 (van 5).
- [ ] ≥2 vistas Athena (van 2: `vw_recaudacion_tuua`, `vw_retrasos_hora_punta`).

---

## Repos relacionados

- [`cloud-computing-proyecto`](https://github.com/btoroled/cloud-computing-proyecto) — documentación central.
- [`ms1-pasajeros-api`](https://github.com/Cloud-MLA) · [`ms2-vuelos-api`](https://github.com/Cloud-MLA) · [`ms3-infraestructura-api`](https://github.com/Cloud-MLA) — los 3 microservicios con BD que este repo ingesta.
- [`ms5-analitica-api`](https://github.com/Cloud-MLA/ms5-analitica-api) — consume las consultas Athena definidas aquí.

---

## Cómo empezar (Guillermo, Mariano, Edinson)

Necesitas los CSV/JSONL de `seeds/` para poder cargar tus 20k+ registros con IDs que crucen con los otros microservicios. Ver [`seeds/README.md`](seeds/README.md).

## Cómo empezar (Fabricio)

1. Terminar `seeds/` — bloquea al equipo.
2. Cuando Guillermo, Mariano y Edinson tengan datos cargados, levantar `ingesta/` para poblar el bucket S3.
3. Crear catálogo Glue, luego portar Q1–Q5 a Athena, luego crear las 2 vistas.
