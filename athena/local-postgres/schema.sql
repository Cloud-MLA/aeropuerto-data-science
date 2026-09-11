-- Esquema unificado para validar las queries Q1..Q5 en Postgres local antes
-- de portarlas a Athena. Un schema por microservicio (ms1/ms2/ms3) imita la
-- futura estructura del catalogo Glue (una database por MS).
--
-- Compatibilidad Athena/Trino: se evitan features Postgres-only. Tipos que
-- difieren se documentan en cada query con -- ATHENA: <cambio necesario>.
--
-- Sin FKs cross-schema — la arquitectura real las hace referencias suaves
-- validadas por REST (contrato §3.2 del plan).

CREATE SCHEMA IF NOT EXISTS ms1;
CREATE SCHEMA IF NOT EXISTS ms2;
CREATE SCHEMA IF NOT EXISTS ms3;

-- =========================================================================
-- MS1 — Pasajeros / Tickets (MySQL en produccion)
-- =========================================================================

CREATE TABLE ms1.categoria_migratoria (
    id           INT           PRIMARY KEY,
    nombre       VARCHAR(30)   NOT NULL,
    tarifa       DECIMAL(10,2) NOT NULL
);

CREATE TABLE ms1.persona (
    id_persona       INT         PRIMARY KEY,
    nombre           VARCHAR(50) NOT NULL,
    apellido         VARCHAR(50) NOT NULL,
    fecha_nacimiento DATE        NOT NULL
);

CREATE TABLE ms1.pasajero (
    id_persona        INT         PRIMARY KEY,
    tipo_documento    VARCHAR(30) NOT NULL,
    numero_documento  VARCHAR(15) NOT NULL,
    id_categoria      INT         NOT NULL
);

CREATE TABLE ms1.ticket (
    id_ticket        INT           PRIMARY KEY,
    precio           DECIMAL(10,2) NOT NULL,
    fecha_emision    DATE          NOT NULL,
    estado_boarding  VARCHAR(20)   NOT NULL,
    id_vuelo         INT           NOT NULL,   -- FK suave a ms2.vuelo
    id_persona       INT           NOT NULL
);

CREATE TABLE ms1.checkin (
    id_ticket      INT         PRIMARY KEY,
    fecha_hora     TIMESTAMPTZ NOT NULL,
    counter        VARCHAR(10) NOT NULL,
    con_equipaje   BOOLEAN     NOT NULL
);

CREATE TABLE ms1.equipaje (
    id           VARCHAR(20)   PRIMARY KEY,
    peso         DECIMAL(6,2)  NOT NULL,
    id_persona   INT           NOT NULL,
    id_vuelo     INT           NOT NULL          -- FK suave a ms2.vuelo
);

-- =========================================================================
-- MS2 — Vuelos / Operaciones (PostgreSQL en produccion)
-- =========================================================================

CREATE TABLE ms2.aerolinea (
    ruc      VARCHAR(11) PRIMARY KEY,
    nombre   VARCHAR(50) NOT NULL,
    alianza  VARCHAR(20) NOT NULL
);

CREATE TABLE ms2.aeronave (
    placa       VARCHAR(11) PRIMARY KEY,
    modelo      VARCHAR(50) NOT NULL,
    fabricante  VARCHAR(50) NOT NULL,
    capacidad   INT         NOT NULL,
    clase       VARCHAR(10) NOT NULL
);

CREATE TABLE ms2.asiento (
    codigo          VARCHAR(5)  NOT NULL,
    placa_aeronave  VARCHAR(11) NOT NULL,
    PRIMARY KEY (codigo, placa_aeronave)
);

CREATE TABLE ms2.empleado (
    id                INT         PRIMARY KEY,
    nombre            VARCHAR(50) NOT NULL,
    apellido          VARCHAR(50) NOT NULL,
    fecha_nacimiento  DATE        NOT NULL
);

CREATE TABLE ms2.tripulacion (
    id_empleado    INT         PRIMARY KEY,
    num_licencia   VARCHAR(20) NOT NULL
);

CREATE TABLE ms2.operativo_tierra (
    id_empleado      INT         PRIMARY KEY,
    area_operativa   VARCHAR(30) NOT NULL
);

CREATE TABLE ms2.vuelo (
    id               INT         PRIMARY KEY,
    num_vuelo        VARCHAR(10) NOT NULL,
    hora_programada  TIMESTAMPTZ NOT NULL,
    hora_real        TIMESTAMPTZ,             -- NULL si estado in {Programado, Embarcando, Cancelado}
    estado           VARCHAR(15) NOT NULL,
    tipo             VARCHAR(15) NOT NULL,    -- Nacional | Internacional
    origen           VARCHAR(4)  NOT NULL,
    destino          VARCHAR(4)  NOT NULL,
    placa_aeronave   VARCHAR(11) NOT NULL,
    ruc_aerolinea    VARCHAR(11) NOT NULL
);

CREATE TABLE ms2.opera_tripulacion (
    id_empleado  INT NOT NULL,
    id_vuelo     INT NOT NULL,
    PRIMARY KEY (id_empleado, id_vuelo)
);

-- =========================================================================
-- MS3 — Infraestructura / Incidencias (MongoDB en produccion, aplanado aqui)
-- =========================================================================
--
-- El contenedor ingesta-ms3 (DS-08) hara este mismo aplanamiento en F2 para
-- que Athena pueda consultar tablas relacionales sobre el data lake.

CREATE TABLE ms3.recurso (
    id                        INT          PRIMARY KEY,
    nombre_tecnico_locacion   VARCHAR(100) NOT NULL,
    tipo                      VARCHAR(10)  NOT NULL,   -- manga | radar
    -- Atributos de manga (NULL si tipo != 'manga')
    estado_acople             VARCHAR(20),
    longitud                  DECIMAL(6,2),
    clase_max                 VARCHAR(10),
    -- Atributos de radar (NULL si tipo != 'radar')
    rango_alcance             INT,
    frecuencia                VARCHAR(20)
);

CREATE TABLE ms3.incidencia (
    id                INT          PRIMARY KEY,
    gravedad          VARCHAR(15)  NOT NULL,
    descripcion       TEXT         NOT NULL,
    tipo_incidencia   VARCHAR(30)  NOT NULL,
    fecha_reporte     TIMESTAMPTZ  NOT NULL,
    fecha_cierre      TIMESTAMPTZ                -- NULL si sigue abierta
);

CREATE TABLE ms3.incidencia_afecta_recurso (
    id_incidencia INT NOT NULL,
    id_recurso    INT NOT NULL,
    PRIMARY KEY (id_incidencia, id_recurso)
);

CREATE TABLE ms3.incidencia_retrasa_vuelo (
    id_incidencia INT NOT NULL,
    id_vuelo      INT NOT NULL,
    PRIMARY KEY (id_incidencia, id_vuelo)
);

CREATE TABLE ms3.asignacion (
    id_vuelo    INT NOT NULL,
    id_recurso  INT NOT NULL,
    PRIMARY KEY (id_vuelo, id_recurso)
);
