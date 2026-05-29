/**
 * frontend/lib/api.ts — Cliente FastAPI para Next.js
 *
 * Fonte: backend/main.py → src/services/
 * Consumido por: todas as páginas do terminal Radar Macro
 *
 * Regras:
 *  - Não calcula nada — apenas busca dados puros.
 *  - Todos os endpoints retornam dict/JSON, nunca HTML.
 *  - Emite erro claro quando API não responde.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// ── fetch util ────────────────────────────────────────────────────────────────

async function fetchJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, v);
    });
  }

  const res = await fetch(url.toString(), {
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    throw new Error(`API error ${res.status} at ${path}: ${await res.text()}`);
  }

  return res.json() as Promise<T>;
}

// ── Health ─────────────────────────────────────────────────────────────────────

export async function getSystemHealth() {
  return fetchJson<{
    status: string;
    timestamp: string;
    services: Record<string, boolean>;
    errors: string[];
  }>("/api/system/health");
}

// ── Trading Desk ──────────────────────────────────────────────────────────────

export async function getTradingLive() {
  return fetchJson<{
    status: string;
    timestamp: string;
    actions: ActionRow[];
    rtd_diagnostic: RTDDiagnostic;
    errors: string[];
  }>("/api/trading/live");
}

export interface ActionRow {
  ticker: string;
  score_final: number;
  score_momentum: number;
  score_tendencia: number;
  score_liquidez: number;
  signal_type: string;
  captured_at: string;
  // extras vindos do DB
  preco?: number;
  variacao?: number;
  volume?: number;
}

export interface RTDDiagnostic {
  last_update: string;
  status: string;
  symbols_covered: number;
  errors: string[];
}

// ── Radar Opportunities ────────────────────────────────────────────────────────

export async function getRadarOpportunities() {
  return fetchJson<{
    status: string;
    timestamp: string;
    opportunities: OpportunityRow[];
    total: number;
    rtd_diagnostic: Record<string, unknown>;
  }>("/api/radar/opportunities");
}

export interface OpportunityRow {
  ticker: string;
  type: string;
  score: number;
  description: string;
}

// ── Opportunities legado ──────────────────────────────────────────────────────

export async function getOpportunities() {
  return fetchJson<OpportunityRow[]>("/api/opportunities");
}

// ── Macro B3 ──────────────────────────────────────────────────────────────────

export interface MacroB3Response {
  status: string;
  errors: string[];
  timestamp: string;
  current_values: {
    selic_meta: number | null;
    ipca_12m: number | null;
    ipca_mensal: number | null;
    ptax: number | null;
    ptax_trend_pct: number | null;
  };
  series: {
    selic: Array<{ date: string; value: number }>;
    ipca_12m: Array<{ date: string; value: number }>;
    ptax_90d: Array<{ date: string; value: number }>;
    igpm_12m: Array<{ date: string; value: number }>;
  };
  regime: {
    regime: string;
    description: string;
    signals: string[];
    selic: number | null;
    ipca_12m: number | null;
    ptax_trend_pct: number | null;
  };
  sector_impact: Array<{
    sector: string;
    impact: string;
    reason: string;
  }>;
}

export async function getMacroB3() {
  return fetchJson<MacroB3Response>("/api/macro/b3");
}

// ── Economic Calendar ─────────────────────────────────────────────────────────

export interface CalendarEvent {
  event: string;
  country: string;
  importance: string;
  source: string;
  previous: string;
  forecast: string;
  actual: string;
}

export interface CalendarDateGroup {
  date: string;
  events: CalendarEvent[];
}

export interface EconomicCalendarResponse {
  status: string;
  errors: string[];
  timestamp: string;
  events: CalendarDateGroup[];
  metrics: { total: number; alta: number; media: number; baixa: number };
  filters: Record<string, unknown>;
}

export async function getEconomicCalendar(params?: {
  start_date?: string;
  end_date?: string;
  countries?: string;
  importances?: string;
  search?: string;
}) {
  return fetchJson<EconomicCalendarResponse>("/api/calendar/economic", params);
}

// ── Valuation ─────────────────────────────────────────────────────────────────

export interface ValuationItem {
  ticker: string;
  integrated_score: number;
  integrated_status: string;
  // M030: These fields come from valuation_results (schema M018)
  status?: string;           // lifecycle status: preliminary/recalculated/approved
  status_label?: string;
  fair_value?: number | null;
  current_price?: number | null;
  upside_pct?: number | null;
  upside_preserved?: number | null;
  upside_recalculated?: number | null;
  method?: string;
  confidence?: string;
  input_quality?: string;
  source_stage?: string;      // M018_CONTROLLED | M018_COMPARISON | M016_LEGACY
  preservation_status?: string | null;
  sanity_check_passed?: boolean | null;
  sanity_status?: string;
  recommended?: boolean;
  valuation_available: boolean;
  created_at: string;
}

export interface ValuationSummaryResponse {
  status: string;
  errors: string[];
  timestamp: string;
  valuations: ValuationItem[];
  preliminary: ValuationItem[];
  summary: ValuationItem[];
  diagnostic: {
    total: number;
    approved: number;
    preliminary?: number;
    pending?: number;
    validated?: number;
    blocked?: number;
    last_update?: string | null;
  };
}

export async function getValuationSummary(ticker?: string, limit = 20) {
  const params: Record<string, string> = { limit: String(limit) };
  if (ticker) params["ticker"] = ticker;
  return fetchJson<ValuationSummaryResponse>("/api/valuation/summary", params);
}

// ── M030: Valuation Detail ────────────────────────────────────────────────────

export interface ValuationSanityCheck {
  check: string;
  result: string;
  passed: boolean | null;
}

export interface ValuationRange {
  low: number | null;
  high: number | null;
}

export interface ValuationDetail {
  status: string;
  ticker: string;
  fair_value: number | null;
  current_price: number | null;
  upside_pct: number | null;
  upside_preserved: number | null;
  upside_recalculated: number | null;
  difference_pct: number | null;
  method: string;
  confidence: string;
  input_quality: string;
  source_stage: string;
  preservation_status: string | null;
  sanity_check_passed: boolean | null;
  block_reason: string | null;
  flags: unknown[];
  recommendation: string | null;
  calculation_notes: string | null;
  lifecycle_status: string;
  status_label: string;
  recommended: boolean;
  sanity_status: string;
  valuation_range: ValuationRange | null;
  bear_case: number | null;
  base_case: number | null;
  bull_case: number | null;
  assumptions: string | null;
  sanity_checks: ValuationSanityCheck[];
  blocked_reasons: string[];
  source: string | null;
  valuation_date: string | null;
  updated_at: string | null;
  errors?: string[];
}

export async function getValuationDetail(ticker: string) {
  return fetchJson<ValuationDetail>(`/api/valuation/${encodeURIComponent(ticker)}`);
}

// ── M030: Valuation Coverage ──────────────────────────────────────────────────

export interface ValuationCoverageItem {
  ticker: string;
  status: string;
  status_label: string;
  fair_value: number | null;
  current_price: number | null;
  upside_pct: number | null;
  method: string;
  sanity_status: string;
  recommended: boolean;
  source: string;
}

export interface ValuationCoverage {
  status: string;
  timestamp: string;
  with_valuation: ValuationCoverageItem[];
  without_valuation: ValuationCoverageItem[];
  total: number;
  with_count: number;
  without_count: number;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  errors?: string[];
}

export async function getValuationCoverage() {
  return fetchJson<ValuationCoverage>("/api/valuation/coverage");
}

// ── Options ────────────────────────────────────────────────────────────────────

export async function getOptionsStrategies() {
  return fetchJson<{
    status: string;
    timestamp: string;
    structures: Array<Record<string, unknown>>;
    watchlist: Array<Record<string, unknown>>;
    history: Array<Record<string, unknown>>;
    diagnostic: Record<string, unknown>;
    errors: string[];
  }>("/api/options/strategies");
}

// ── M024: Watchlist ────────────────────────────────────────────────────────────

export interface WatchlistItem {
  ticker: string;
  name: string | null;
  sector: string | null;
  price: number | null;
  variacao_pct: number | null;
  price_source: string | null;
  score: number;
  direction: string;
  status: string;
  risk: string;
  liquidity: number;
  adv_21d: number | null;
  next_action: string | null;
  governance_blocked: boolean;
  has_options: boolean;
  has_valuation: boolean;
  data_quality: string | null;
  source: string;
  updated_at: string;
}

export interface WatchlistResponse {
  status: string;
  errors: string[];
  timestamp: string;
  tickers: WatchlistItem[];
  total: number;
  counts: {
    buy: number;
    sell: number;
    hold: number;
  } | null;
  diagnostic: {
    source: string;
    count: number;
    has_prices: boolean;
    has_sectors: boolean;
    has_variacao: boolean;
    has_adv: boolean;
    has_options: boolean;
    has_valuation: boolean;
    enriched: boolean;
  } | null;
}

export async function getWatchlist() {
  return fetchJson<WatchlistResponse>("/api/watchlist");
}

// ── M024: Quant Signals ────────────────────────────────────────────────────────

export interface QuantSignal {
  ticker: string;
  score_final: number;
  // API returns momentum_score / trend_score (actual values)
  momentum_score: number | null;
  trend_score: number | null;
  // Legacy aliases kept for backward compat (always null from API)
  momentum: number | null;
  tendencia: number | null;
  liquidez: number | null;
  volatilidade: number | null;
  direction: string;
  direction_tech?: string;
  gatilho: string;
  risco: string;
  proxima_acao: string | null;
  governance_blocked?: boolean;
  volume_score?: number | null;
  breakout_score?: number | null;
  support_resistance_score?: number | null;
  technical_score?: number | null;
  technical_status?: string | null;
  score_tecnico?: number | null;
  volume_21d?: number | null;
  negocios_21d?: number | null;
  sector?: string | null;
  timestamp: string;
}

export interface QuantSignalsResponse {
  status: string;
  errors: string[];
  timestamp: string;
  ranking: QuantSignal[];
  total: number;
  counts: {
    buy: number;
    sell: number;
    hold: number;
    watch: number;
  };
  diagnostic: {
    source: string;
    count: number;
    has_momentum: boolean;
    has_tendencia: boolean;
  };
}

export async function getQuantSignals() {
  return fetchJson<QuantSignalsResponse>("/api/quant/signals");
}

// ── M024: Signal Matrix ────────────────────────────────────────────────────────

// API real: src/services/signal_matrix_service.py
// Blocos sem dados mostram "em integração", não zero.

export interface SignalBlock {
  status: string;       // "disponível" | "em integração"
  score?: number | null;
  label?: string | null;
  evidencia?: string | null;
  fonte?: string | null;
  regime?: string | null;
  tendencia?: string | null;
  confidence?: number | null;
  estrutura?: string | null;
  iv_rank?: number | null;
  payoff?: string | null;
  liquidez?: number | null;
  fair_value?: number | null;
  preco?: number | null;
  upside_pct?: number | null;
  metodo?: string | null;
  risk_status?: string | null;
  var_95?: number | null;
  shortfall?: number | null;
  explanation?: string | null;
}

export interface SignalConclusao {
  status: string;
  recommendation: string;
  confidence: number;
}

export interface SignalMatrixAsset {
  ticker: string;
  blocos: {
    tecnico: SignalBlock;
    momentum: SignalBlock;
    liquidez: SignalBlock;
    macro: SignalBlock;
    opcoes: SignalBlock;
    valuation: SignalBlock;
    risco: SignalBlock;
  };
  score_agregado: number | null;
  conflitos: string[];
  conclusao: SignalConclusao;
  name?: string | null;
  sector?: string | null;
  updated_at?: string;
}

export interface SignalMatrixResponse {
  status: string;
  errors: string[];
  timestamp: string;
  assets: SignalMatrixAsset[];
  total: number;
  diagnostic: {
    last_update: string | null;
    table: string;
  };
}

export async function getSignalMatrix(ticker?: string, limit = 20) {
  const params: Record<string, string> = { limit: String(limit) };
  if (ticker) params["ticker"] = ticker;
  return fetchJson<SignalMatrixResponse>("/api/ai/signal-matrix", params);
}

// ── M024: Thesis Builder ──────────────────────────────────────────────────────

export interface ThesisEvidence {
  text: string;
  source: string;
  weight: string;
}

export interface ThesisCatalyst {
  label: string;
  expected_date: string | null;
  impact: string;
  probability: string;
}

export interface ThesisItem {
  ticker: string;
  name: string | null;
  sector: string | null;
  sentiment: string;
  conviction_score: number;
  confidence_label: string;
  hypothesis: string;
  bull_case: ThesisEvidence[];
  bear_case: ThesisEvidence[];
  drivers: ThesisCatalyst[];
  risks: string[];
  indicators_used: string[];
  price_target: number | null;
  fair_value: number | null;
  upside_pct: number | null;
  updated_at: string;
}

export interface ThesisResponse {
  status: string;
  errors: string[];
  timestamp: string;
  theses: ThesisItem[];
  total: number;
  counts: {
    complete: number;
    integrating: number;
  } | null;
  diagnostic: {
    last_update: string | null;
    table: string;
  };
}

export async function getThesis(ticker?: string, limit = 10) {
  const params: Record<string, string> = { limit: String(limit) };
  if (ticker) params["ticker"] = ticker;
  return fetchJson<ThesisResponse>("/api/ai/thesis", params);
}

// ── M024: Conviction Desk ──────────────────────────────────────────────────────

export interface ConvictionPosition {
  ticker: string;
  score: number;
  upside_pct?: number | null;
  status?: string | null;
  conviction_level?: string | null;
  change?: number | null;
  rationale?: string | null;
  signal_type?: string | null;
  timestamp?: string | null;
  has_history?: boolean | null;
  change_direction?: string | null;
  from_score?: number | null;
  to_score?: number | null;
}

export interface ConvictionResponse {
  status: string;
  errors: string[];
  timestamp: string;
  positions: ConvictionPosition[];
  total: number;
  counts: {
    high: number;
    medium: number;
    low: number;
  } | null;
  empty_state: boolean;
  note: string | null;
}

export async function getConvictionPositions(limit = 20, days = 30) {
  const params: Record<string, string> = {
    limit: String(limit),
    days: String(days),
  };
  return fetchJson<ConvictionResponse>("/api/conviction/positions", params);
}

// ── M024: Agent Runtime ───────────────────────────────────────────────────────

export interface ServiceStatus {
  name: string;
  status: string;
  latency_ms: number;
  details: Record<string, unknown>;
}

export interface TableCount {
  table: string;
  count: number;
  last_update: string | null;
}

export interface RTDFile {
  name: string;
  path: string;
  size_kb: number;
  modified: string;
  age_minutes: number;
}

export interface AgentEndpoint {
  path: string;
  method: string;
  source: string;
}

export interface AgentRuntimeResponse {
  status: string;
  errors: string[];
  timestamp: string;
  backend_status: string;
  services_status: ServiceStatus[];
  db_status: {
    db_path: string;
    db_exists: boolean;
    table_counts: Record<string, number>;
    last_updates: Record<string, string | null>;
    ok: boolean;
  };
  rtd_files: RTDFile[];
  rtd_count: number;
  services_available: Array<{
    name: string;
    module: string;
    function: string;
    available: boolean;
  }>;
  available_count: number;
  total_services: number;
  new_services: number;
  endpoints: AgentEndpoint[];
  total_endpoints: number;
}

// ── M029: Market Data Core — Histórico de Ações ────────────────────────────────

export interface OHLCVSnapshot {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  close_prev: number | null;
  volume: number | null;
  trades: number | null;
  vwap: number | null;
}

export interface AssetHistorySummary {
  last_close: number | null;
  variacao_dia: number | null;
  nome: string;
  classe: string;
  vwap: number | null;
  rsi: number | null;
  macd: number | null;
  adx: number | null;
  bollinger_b: number | null;
  hilo: number | null;
  volatilidade_hist: number | null;
  volatilidade_hist_media: number | null;
  return_semana: number | null;
  return_mes: number | null;
  return_3m: number | null;
  return_6m: number | null;
  return_12m: number | null;
  return_ytd: number | null;
  volume_media: number | null;
  trades_media: number | null;
}

export interface AssetHistoryResponse {
  status: string;
  ticker: string;
  ticker_matched: string | null;
  period: string;
  period_available: string;
  ohlcv: OHLCVSnapshot | null;
  indicators: {
    rsi: number | null;
    macd: number | null;
    adx: number | null;
    bollinger_b: number | null;
    hilo: number | null;
    volatilidade_hist: number | null;
  };
  summary: AssetHistorySummary;
  source: string;
  timestamp: string;
  diagnostic: Record<string, unknown>;
}

export async function getAssetHistory(ticker: string, period = "1y") {
  return fetchJson<AssetHistoryResponse>(
    `/api/market/assets/${encodeURIComponent(ticker)}/history`,
    { period }
  );
}

export interface AssetSummaryRow {
  ticker: string;
  ticker_matched: string | null;
  last_close: number | null;
  variacao_dia: number | null;
  classe: string;
  rsi: number | null;
  adx: number | null;
  return_semana: number | null;
  return_mes: number | null;
  return_3m: number | null;
  volatilidade: number | null;
  nome: string;
}

export interface MarketHistorySummaryResponse {
  status: string;
  total: number;
  missing: string[];
  tickers: AssetSummaryRow[];
  source: string;
  timestamp: string;
  diagnostic: Record<string, unknown>;
}

export async function getMarketHistorySummary(tickers: string[]) {
  return fetchJson<MarketHistorySummaryResponse>(
    "/api/market/assets/history-summary",
    { tickers: tickers.join(",") }
  );
}

export interface AllActionsResponse {
  status: string;
  total: number;
  actions: Array<{
    ticker: string;
    nome: string;
    preco: number | null;
    variacao: number | null;
    variacao_pts: number | null;
    abertura: number | null;
    maxima: number | null;
    minima: number | null;
    fechamento_anterior: number | null;
    volume: number | null;
    negocios: number | null;
    vwap: number | null;
    bid: number | null;
    ask: number | null;
    rsi: number | null;
    macd: number | null;
    adx: number | null;
    bollinger_b: number | null;
    hilo: number | null;
    volatilidade: number | null;
    meta_semana: number | null;
    meta_mes: number | null;
    meta_3m: number | null;
    meta_6m: number | null;
    meta_12m: number | null;
    timestamp: string;
  }>;
  source: string;
  timestamp: string;
  diagnostic: Record<string, unknown>;
}

export async function getAllActions() {
  return fetchJson<AllActionsResponse>("/api/market/actions");
}

// ── M029: Opções — Cadeia de Opções ──────────────────────────────────────────

export interface OptionEntry {
  ticker: string;
  option_type: string;
  strike: number | null;
  expiration_date: string | null;
  dte: number | null;
  dte_category: string | null;
  last_price: number | null;
  bid: number | null;
  ask: number | null;
  spread_pct: number | null;
  volume: number | null;
  trades: number | null;
  open_interest: number | null;
  implied_volatility: number | null;
  delta: number | null;
  gamma: number | null;
  theta: number | null;
  rho: number | null;
  vega: number | null;
  moneyness: string;
  liquidity_score: number | null;
  score?: number | null;
  cenario?: string | null;
  estruturas_sugeridas?: string | null;
  status: string;
  motivo?: string | null;
  source: string;
  data_analise?: string | null;
}

export interface OptionsChainResponse {
  status: string;
  underlying: string;
  spot_price: number | null;
  expirations: string[];
  calls_count: number;
  puts_count: number;
  calls: OptionEntry[];
  puts: OptionEntry[];
  total_options: number;
  has_live_data: boolean;
  source: string;
  timestamp: string;
  diagnostic: Record<string, unknown>;
}

export async function getOptionsChain(underlying: string, expiration?: string) {
  const params: Record<string, string> = {};
  if (expiration) params["expiration"] = expiration;
  return fetchJson<OptionsChainResponse>(
    `/api/options/chain/${encodeURIComponent(underlying)}`,
    params
  );
}

// ── M029: Opções — Histórico de Opção ─────────────────────────────────────────

export interface OptionHistoryRecord {
  date: string;
  last_price: number | null;
  spot: number | null;
  bid?: number | null;
  ask?: number | null;
  strike: number | null;
  moneyness: string;
  dte: number | null;
  volume_5d: number | null;
  volume_10d: number | null;
  volume_21d: number | null;
  negocios_5d: number | null;
  variacao_preco: number | null;
  retorno_5d: number | null;
  retorno_21d: number | null;
  retorno_63d: number | null;
  score: number | null;
  liquidity_score?: number | null;
  status: string;
  cenario: string | null;
  estruturas_sugeridas: string | null;
  implied_volatility?: number | null;
  delta?: number | null;
  gamma?: number | null;
  theta?: number | null;
  vega?: number | null;
}

export interface OptionHistoryResponse {
  status: string;
  ticker: string;
  underlying: string;
  option_type: string;
  period: string;
  records: OptionHistoryRecord[];
  summary: {
    record_count: number;
    earliest_date: string | null;
    latest_date: string | null;
    current_price: number | null;
    max_price: number | null;
    min_price: number | null;
    avg_price: number | null;
    latest_score: number | null;
    latest_status: string | null;
  };
  source: string;
  timestamp: string;
  diagnostic: Record<string, unknown>;
}

export async function getOptionHistory(option_ticker: string, period = "6m") {
  return fetchJson<OptionHistoryResponse>(
    `/api/options/history/${encodeURIComponent(option_ticker)}`,
    { period }
  );
}

// ── M029: Opções — Radar ─────────────────────────────────────────────────────

// Normalize a raw option row (from legacy CSVs) to the OptionEntry schema.
// Handles: tipo→option_type, vencimento→expiration_date, ultimo_preco→last_price,
// ativo_objeto→underlying, negocios→trades, spot→underlying, moneyness_cat→moneyness.
function normalizeOptionRow(row: Record<string, unknown>): Record<string, unknown> {
  return {
    ticker: row.ticker ?? row.ticker_opcao ?? "",
    underlying: row.underlying ?? row.ativo_objeto ?? row.spot ?? "",
    option_type: row.option_type ?? row.tipo ?? "CALL",
    strike: row.strike != null ? Number(row.strike) : null,
    expiration_date: row.expiration_date ?? row.vencimento ?? null,
    dte: row.dte != null ? Number(row.dte) : null,
    last_price: row.last_price ?? row.ultimo_preco ?? row.close ?? null,
    bid: row.bid != null ? Number(row.bid) : null,
    ask: row.ask != null ? Number(row.ask) : null,
    spread_pct: row.spread_pct != null ? Number(row.spread_pct) : null,
    volume: row.volume != null ? Number(row.volume) : null,
    trades: row.trades ?? row.negocios ?? null,
    open_interest: row.open_interest != null ? Number(row.open_interest) : null,
    implied_volatility: row.implied_volatility != null ? Number(row.implied_volatility) : null,
    delta: row.delta != null ? Number(row.delta) : null,
    gamma: row.gamma != null ? Number(row.gamma) : null,
    theta: row.theta != null ? Number(row.theta) : null,
    rho: row.rho != null ? Number(row.rho) : null,
    vega: row.vega != null ? Number(row.vega) : null,
    moneyness: row.moneyness ?? row.moneyness_cat ?? "N/A",
    liquidity_score: row.liquidity_score != null ? Number(row.liquidity_score) : null,
    score: row.score != null ? Number(row.score) : null,
    cenario: row.cenario ?? null,
    estruturas_sugeridas: row.estruturas_sugeridas ?? null,
    status: row.status ?? "UNKNOWN",
    motivo: row.motivo ?? null,
    source: row.source ?? "unknown",
    data_analise: row.data_analise ?? null,
  } as Record<string, unknown>;
}

export interface OptionsRadarResponse {
  status: string;
  total: number;
  underlying_filter: string | null;
  by_status: Record<string, number>;
  by_underlying: Record<string, {
    total: number;
    calls: number;
    puts: number;
    calls_list: OptionEntry[];
    puts_list: OptionEntry[];
  }>;
  candidates_next_session: OptionEntry[];
  monitor_rtd: OptionEntry[];
  aguardar_liquidez: OptionEntry[];
  total_candidates: number;
  total_monitor_rtd: number;
  rtd_diagnostic: Record<string, {
    spot: number | null;
    limite: number | null;
    com_liquidez: number | null;
    oportunidades: number | null;
    status: string;
  }>;
  source: string;
  timestamp: string;
  diagnostic: Record<string, unknown>;
}

export async function getOptionsRadar(underlying?: string) {
  const params: Record<string, string> = {};
  if (underlying) params["underlying"] = underlying;
  const raw = await fetchJson<Record<string, unknown>>("/api/options/radar", params);

  // Normalize all option lists to the OptionEntry schema
  function normList(rows: unknown[]): OptionEntry[] {
    return (rows as Record<string, unknown>[]).map((r) => normalizeOptionRow(r) as unknown as OptionEntry);
  }

  const normalized: OptionsRadarResponse = {
    status: raw.status as string,
    total: raw.total as number,
    underlying_filter: raw.underlying_filter as string | null,
    by_status: (raw.by_status as Record<string, number>) ?? {},
    by_underlying: Object.fromEntries(
      Object.entries(raw.by_underlying as Record<string, {
        total: number; calls: number; puts: number;
        calls_list: unknown[]; puts_list: unknown[];
      }> ?? {}).map(([k, v]) => [k, {
        total: v.total,
        calls: v.calls,
        puts: v.puts,
        calls_list: normList(v.calls_list),
        puts_list: normList(v.puts_list),
      }])
    ) as OptionsRadarResponse["by_underlying"],
    candidates_next_session: normList((raw.candidates_next_session as unknown[]) ?? []),
    monitor_rtd: normList((raw.monitor_rtd as unknown[]) ?? []),
    aguardar_liquidez: normList((raw.aguardar_liquidez as unknown[]) ?? []),
    total_candidates: raw.total_candidates as number,
    total_monitor_rtd: raw.total_monitor_rtd as number,
    rtd_diagnostic: (raw.rtd_diagnostic as Record<string, {
      spot: number | null; limite: number | null;
      com_liquidez: number | null; oportunidades: number | null; status: string;
    }>) ?? {},
    source: raw.source as string,
    timestamp: raw.timestamp as string,
    diagnostic: (raw.diagnostic as Record<string, unknown>) ?? {},
  };

  return normalized;
}

// ── M029: Futuros — Live ──────────────────────────────────────────────────────

export interface FutureEntry {
  ticker: string;
  classe: string;
  contract_type: string | null;
  nome: string;
  price: number | null;
  variation: number | null;
  variation_pts: number | null;
  volume: number | null;
  trades: number | null;
  bid: number | null;
  ask: number | null;
  spread: number | null;
  spread_pct: number | null;
  vwap: number | null;
  aba_origem: string;
  status: string;
  updated_at: string;
}

export interface FuturesLiveResponse {
  status: string;
  futures: FutureEntry[];
  indices: FutureEntry[];
  total: number;
  futures_count: number;
  indices_count: number;
  source: string;
  timestamp: string;
  diagnostic: Record<string, unknown>;
}

export async function getFuturesLive() {
  return fetchJson<FuturesLiveResponse>("/api/futures/live");
}

export interface FuturesSummaryResponse extends FuturesLiveResponse {
  summary: {
    total: number;
    futures_count: number;
    indices_count: number;
    ao_vivo: number;
    by_ticker: Record<string, {
      classe: string;
      price: number | null;
      variation: number | null;
      variation_pts: number | null;
      volume: number | null;
      trades: number | null;
      status: string;
    }>;
    ibov: number | null;
  };
}

export async function getFuturesSummary() {
  return fetchJson<FuturesSummaryResponse>("/api/futures/summary");
}

export async function getAgentStatus() {
  return fetchJson<AgentRuntimeResponse>("/api/agents/status");
}