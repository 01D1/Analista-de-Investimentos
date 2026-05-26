-- migrations/002_valuation_results.sql
-- M018-S01: Valuation Result Schema and Safe Writer
-- Criado em: 2026-05-26
--
-- Regras imutáveis desta migration:
--   RULE-01  Não sobrescrever fair_values PRESERVE_EXISTING sem force_recalc=True
--   RULE-02  preliminary_fair_value ≠ approved_fair_value — ciclo de vida obrigatório
--   RULE-03  Nenhuma escrita em asset_intelligence_snapshots em M018
--   RULE-16  Backup de scanner_quant.db antes de qualquer migration
--
-- Aplicar via: src/valuation/valuation_results_store.py → ensure_valuation_results_schema()
-- OU: sqlite3 data/ingestion.db < migrations/002_valuation_results.sql
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS valuation_results (
    -- Identidade
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                  TEXT    NOT NULL,
    valuation_date          DATE    NOT NULL,

    -- Lifecycle status: 'preliminary' | 'validated' | 'approved'
    status                  TEXT    NOT NULL DEFAULT 'preliminary',

    -- Valores por ciclo de vida
    preserved_fair_value    REAL,           -- legado M016 (só PRESERVE_EXISTING)
    recalculated_fair_value REAL,           -- M018-S02: cálculo novo em modo comparação
    preliminary_fair_value  REAL,           -- M018-S03: calculado, não validado
    validated_fair_value    REAL,           -- aprovado humano ou S04 automático
    approved_fair_value     REAL,           -- promovido a oficial (escopo M019)

    -- Contexto de mercado no momento do cálculo
    market_price            REAL,
    upside_pct              REAL,           -- (effective_fair_value / market_price - 1) × 100
    upside_preserved        REAL,           -- upside usando preserved_fair_value
    upside_recalculated     REAL,           -- upside usando recalculated_fair_value
    difference_pct          REAL,           -- (recalc / preserved - 1) × 100 (PRESERVE_EXISTING only)

    -- Metadados do cálculo
    method_used             TEXT    NOT NULL,  -- 'DDM' | 'DCF' | 'EV_EBITDA' | 'HYBRID'
    confidence              TEXT    NOT NULL,  -- 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT'
    input_quality           TEXT    NOT NULL,  -- 'FULL' | 'PARTIAL' | 'DISTRESSED' | 'MANUAL_REVIEW'
    source                  TEXT    NOT NULL,  -- 'M018_CONTROLLED' | 'M018_COMPARISON' | 'M016_LEGACY'

    -- Classificação para PRESERVE_EXISTING
    preservation_status     TEXT,           -- 'KEEP_PRESERVED' | 'REVIEW_PRESERVED'
                                            -- | 'REPLACE_CANDIDATE' | 'INSUFFICIENT_DATA'

    -- Controle de sanidade e flags
    sanity_check_passed     INTEGER,        -- 0 | 1 | NULL (não avaliado ainda)
    block_reason            TEXT,           -- motivo de bloqueio quando sanity=0
    flags                   TEXT,           -- JSON array: ["distressed_risk", "qualidade_media", ...]

    -- Recomendação de investimento (definida em etapa futura)
    recommendation          TEXT,           -- 'COMPRAR' | 'MANTER' | 'VENDER' | NULL

    -- Rastreabilidade
    calculation_notes       TEXT,
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    promoted_at             DATETIME,

    -- Unicidade: (ticker, data, fonte) — uma linha por ciclo de cálculo
    UNIQUE(ticker, valuation_date, source)
);

-- Índices de acesso frequente
CREATE INDEX IF NOT EXISTS idx_vr_ticker
    ON valuation_results(ticker);

CREATE INDEX IF NOT EXISTS idx_vr_ticker_date
    ON valuation_results(ticker, valuation_date DESC);

CREATE INDEX IF NOT EXISTS idx_vr_status
    ON valuation_results(status);

CREATE INDEX IF NOT EXISTS idx_vr_source
    ON valuation_results(source);

CREATE INDEX IF NOT EXISTS idx_vr_sanity
    ON valuation_results(sanity_check_passed);
