-- =========================================================================
-- Auditoría Edu · Setup de Supabase
-- Correr UNA SOLA VEZ en el SQL Editor del proyecto Supabase.
-- Crea la tabla, los índices, el dedup por (tipo, comprobante, codigo)
-- y deja RLS activada (service_role bypassa RLS, así que Apps Script escribe).
-- =========================================================================

-- Enum para tipo de movimiento
DO $$ BEGIN
  CREATE TYPE tipo_mov AS ENUM ('envio', 'recibo');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Tabla central
CREATE TABLE IF NOT EXISTS registro_movimiento (
  id                   BIGSERIAL PRIMARY KEY,
  creado_en_origen     TIMESTAMPTZ NOT NULL,
  email_carga          VARCHAR(160) NOT NULL DEFAULT '',
  nombre_carga         VARCHAR(120) DEFAULT '',
  tipo                 tipo_mov    NOT NULL,
  sector_salida        VARCHAR(60) NOT NULL DEFAULT '',
  sector_entrada       VARCHAR(60) DEFAULT '',
  codigo               VARCHAR(50) NOT NULL,
  descripcion          VARCHAR(160) DEFAULT '',
  cantidad_bultos      INT NOT NULL DEFAULT 0 CHECK (cantidad_bultos    >= 0),
  unidades_por_bulto   INT NOT NULL DEFAULT 0 CHECK (unidades_por_bulto >= 0),
  unidades_sueltas     INT NOT NULL DEFAULT 0 CHECK (unidades_sueltas   >= 0),
  observaciones        TEXT DEFAULT '',
  comprobante          VARCHAR(30) DEFAULT '',
  estado_concil        VARCHAR(20) DEFAULT '',
  estado_real          VARCHAR(40) DEFAULT '',
  obs_cande            TEXT DEFAULT '',
  flag_g3              VARCHAR(30) DEFAULT '',
  ref_bejerman         VARCHAR(30) DEFAULT '',
  -- Columnas calculadas en BD: Django ni Apps Script las envían
  total_unidades       INT GENERATED ALWAYS AS
                         (cantidad_bultos * unidades_por_bulto + unidades_sueltas) STORED,
  mes                  DATE GENERATED ALWAYS AS
                         (date_trunc('month', creado_en_origen)::date) STORED,
  creado_en            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Dedup: la misma combinación (tipo, comprobante, codigo) sólo entra una vez.
-- Filas sin comprobante no participan del índice (no dedupea).
CREATE UNIQUE INDEX IF NOT EXISTS uq_mov_tipo_comp_cod
  ON registro_movimiento (tipo, comprobante, codigo)
  WHERE comprobante <> '';

-- Índices para las consultas del dashboard
CREATE INDEX IF NOT EXISTS ix_mov_cod_fecha
  ON registro_movimiento (codigo, creado_en_origen DESC);
CREATE INDEX IF NOT EXISTS ix_mov_sal_fecha
  ON registro_movimiento (sector_salida, creado_en_origen DESC);
CREATE INDEX IF NOT EXISTS ix_mov_tipo_mes
  ON registro_movimiento (tipo, mes DESC);

-- RLS: activada por default en Supabase. service_role la bypassa, anon no.
-- Esto significa que Apps Script (usa service_role) puede escribir;
-- el cliente web (anon) no puede leer ni escribir desde el navegador.
ALTER TABLE registro_movimiento ENABLE ROW LEVEL SECURITY;

-- Política explícita de NO acceso a anon ni authenticated.
-- La app Django lee con conexión Postgres directa (sin PostgREST), así que
-- las policies no la afectan — pasa por el rol postgres, no por anon/auth.
-- (No creamos policies para anon/authenticated: por default, sin policy = sin acceso.)

-- Vista opcional para consultas agregadas (si alguna vez querés usarla desde Django)
CREATE OR REPLACE VIEW v_resumen_mensual AS
SELECT codigo, mes, sector_salida, tipo,
       SUM(total_unidades)  AS total_unidades,
       SUM(cantidad_bultos) AS total_bultos,
       COUNT(*)             AS n_registros
FROM   registro_movimiento
GROUP  BY codigo, mes, sector_salida, tipo;

-- Fin del setup.
-- Ejecutá un SELECT para confirmar: SELECT COUNT(*) FROM registro_movimiento;
