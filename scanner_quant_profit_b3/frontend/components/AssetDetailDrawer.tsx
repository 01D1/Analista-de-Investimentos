"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  getSelectedTicker,
  subscribeDrawer,
  closeDrawer,
} from "@/lib/drawerStore";

interface ApiResponse {
  status: string;
  errors?: (string | Record<string, unknown>)[];
  timestamp: string;
  watchlist?: {
    status: string;
    items?: WatchlistItem[];
  } | null;
  quant_signals?: {
    status: string;
    ranking?: QuantSignalItem[];
  } | null;
  signal_matrix?: {
    status: string;
    assets?: MatrixAsset[];
  } | null;
  thesis?: {
    status: string;
    theses?: ThesisItem[];
  } | null;
  macro?: {
    status: string;
    current_values?: {
      selic_meta: number | null;
      ipca_12m: number | null;
      ptax: number | null;
      ptax_trend_pct: number | null;
    };
    regime?: {
      regime: string;
      description: string;
      signals: string[];
    };
    sector_impact?: Array<{ sector: string; impact: string; reason: string }>;
  } | null;
  options_strategies?: {
    status: string;
    structures?: unknown[];
    watchlist?: unknown[];
    diagnostic?: Record<string, unknown>;
  } | null;
  valuation?: {
    status: string;
    summary?: ValuationSummaryItem[];
  } | null;
  conviction?: {
    status: string;
    positions?: ConvictionPosition[];
  } | null;
}

// M029 — Market History interfaces
interface OHLCVSnapshot {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  trades: number | null;
  vwap: number | null;
}

interface AssetHistoryData {
  status: string;
  ticker: string;
  ohlcv: OHLCVSnapshot | null;
  indicators: {
    rsi: number | null;
    macd: number | null;
    adx: number | null;
    bollinger_b: number | null;
    hilo: number | null;
    volatilidade_hist: number | null;
  };
  summary: {
    last_close: number | null;
    variacao_dia: number | null;
    nome: string;
    classe: string;
    vwap: number | null;
    return_semana: number | null;
    return_mes: number | null;
    return_3m: number | null;
    return_6m: number | null;
    return_12m: number | null;
    return_ytd: number | null;
  };
  source?: string;
}

// M029 — Options interfaces
interface OptionEntry {
  ticker: string;
  option_type: string;
  strike: number | null;
  expiration_date: string | null;
  dte: number | null;
  last_price: number | null;
  bid: number | null;
  ask: number | null;
  spread_pct: number | null;
  volume: number | null;
  trades: number | null;
  implied_volatility: number | null;
  delta: number | null;
  gamma: number | null;
  theta: number | null;
  vega: number | null;
  score: number | null;
  status: string;
  source: string;
}

interface OptionsChainData {
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
}

interface WatchlistItem {
  ticker: string;
  name: string | null;
  sector: string | null;
  price: number | null;
  variacao_pct: number | null;
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
  source: string;
  updated_at: string;
}

interface QuantSignalItem {
  ticker: string;
  score_final: number;
  momentum_score: number | null;
  trend_score: number | null;
  liquidez: number | null;
  volatilidade: number | null;
  technical_score: number;
  technical_status: string;
  direction: string;
  direction_tech: string;
  gatilho: string;
  risco: string;
  proxima_acao: string | null;
  volume_21d: number | null;
  negocios_21d: number | null;
  timestamp: string;
  governance_blocked: boolean;
  tech_fonte: string;
  vol_fonte: string;
}

interface SignalBlock {
  status: string;
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
  fair_value?: number | null;
  preco?: number | null;
  upside_pct?: number | null;
  metodo?: string | null;
  risk_status?: string | null;
  var_95?: number | null;
  shortfall?: number | null;
  // technico_indicadores fields
  technical_status?: string | null;
  momentum_score?: number | null;
  trend_score?: number | null;
  volume_score?: number | null;
  breakout_score?: number | null;
  support_resistance_score?: number | null;
  // opcoes liquidity
  liquidez?: number | null;
  // volatilidade from tecnico_indicadores
  volatilidade?: number | null;
}

interface MatrixAsset {
  ticker: string;
  blocos?: {
    tecnico?: SignalBlock;
    tecnico_indicadores?: SignalBlock;
    momentum?: SignalBlock;
    liquidez?: SignalBlock;
    macro?: SignalBlock;
    opcoes?: SignalBlock;
    valuation?: SignalBlock;
    risco?: SignalBlock;
  };
  score_agregado: number | null;
  conflitos: string[];
  conclusao?: {
    status: string;
    recommendation: string;
    confidence: number;
  };
  name?: string | null;
  sector?: string | null;
  updated_at?: string;
}

interface ThesisItem {
  ticker: string;
  name: string | null;
  sentiment: string;
  conviction_score: number;
  hipotese_principal: string;
  tese_bullish?: Array<{ text: string; weight: string; source: string }>;
  tese_bearish?: Array<{ text: string; weight: string; source: string }>;
  evidencias_bullish: unknown[];
  evidencias_bearish: unknown[];
  fatores_risco?: Array<{ texto: string; severidade: string; fonte: string }>;
  catalisadores: unknown[];
  indicadores_usados: string[];
  sinais_tecnicos?: Record<string, unknown>;
  contexto_macro?: Record<string, unknown>;
  price_target: number | null;
  fair_value: number | null;
  upside_pct: number | null;
  updated_at: string;
}

interface ValuationSummaryItem {
  ticker: string;
  integrated_score: number;
  integrated_status: string;
  upside_pct: number;
  valuation_available: boolean;
  created_at: string;
}

interface ConvictionPosition {
  ticker: string;
  score: number;
  upside_pct?: number | null;
  status?: string | null;
  conviction_level?: string | null;
  change?: number | null;
  from_score?: number | null;
  to_score?: number | null;
  rationale?: string | null;
  signal_type?: string | null;
  timestamp?: string | null;
  governance_blocked: boolean;
  has_history?: boolean | null;
}

// ── helpers ──────────────────────────────────────────────────────────────────

function scoreColor(score: number | null | undefined): string {
  if (score == null) return "var(--fg-5)";
  if (score >= 70) return "var(--pos)";
  if (score >= 50) return "var(--warn)";
  return "var(--neg)";
}

function directionBadge(dir: string): string {
  const d = (dir ?? "").toUpperCase();
  if (d === "BUY" || d === "COMPRA") return "badge-buy";
  if (d === "SELL" || d === "VENDA") return "badge-sell";
  return "badge-neutral";
}

function directionLabel(dir: string): string {
  const d = (dir ?? "").toUpperCase();
  const map: Record<string, string> = {
    BUY: "BUY", COMPRA: "COMPRA",
    SELL: "SELL", VENDA: "VENDA",
    HOLD: "HOLD", WATCH: "WATCH",
  };
  return (map[d] ?? d) || "—";
}

function blockBadge(status: string | undefined): string {
  if (status === "disponível") return "badge-buy";
  if (status === "em integração") return "badge-cyan";
  return "badge-neutral";
}

function blockLabel(status: string | undefined): string {
  if (status === "disponível") return "disponível";
  if (status === "em integração") return "em integração";
  return "indisponível";
}

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return `${Math.floor(diff / 86400)}d`;
  } catch {
    return "—";
  }
}

function fmtLocal(val: number | null | undefined, unit = ""): string {
  if (val == null) return "—";
  return `${val.toFixed(1)}${unit}`;
}

function unavailable(val: unknown): string {
  if (val == null || val === null || val === undefined) return "indisponível";
  return String(val);
}

// ── Block renderers ───────────────────────────────────────────────────────────

function BlockSection({
  label,
  status,
  children,
}: {
  label: string;
  status: string | undefined;
  children: React.ReactNode;
}) {
  const s = status ?? "—";
  return (
    <div className="add-section">
      <div className="add-section-header">
        <span className="add-section-label">{label}</span>
        <span className={`badge ${blockBadge(s)}`}>{blockLabel(s)}</span>
      </div>
      {s === "disponível" ? (
        children
      ) : (
        <div className="add-unavailable">aguardando dados</div>
      )}
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="add-meta-row">
      <span className="add-meta-key">{label}</span>
      <span className="add-meta-val">{unavailable(value)}</span>
    </div>
  );
}

// ── Drawer component ──────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-unused-vars
interface Props {
  /** Provided for future extension — not currently used */
  onTickerChange?: (ticker: string) => void;
}

export default function AssetDetailDrawer() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ApiResponse | null>(null);

  // M029 — market history + options data
  const [historyData, setHistoryData] = useState<AssetHistoryData | null>(null);
  const [optionsChain, setOptionsChain] = useState<OptionsChainData | null>(null);
  const [loadingMarket, setLoadingMarket] = useState(false);

  // M029 — active tab: visao_geral | historico | opcoes
  const [activeTab, setActiveTab] = useState<"visao_geral" | "historico" | "opcoes">("visao_geral");

  // Subscribe to global drawer store — read state directly, no setState in effect body
  const currentTicker = getSelectedTicker();
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (currentTicker !== selectedTicker) setSelectedTicker(currentTicker);
    return subscribeDrawer((ticker) => {
      setSelectedTicker(ticker);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentional: subscribe once, ticker read from closure

  // used internally only — use ref to avoid stale closure while allowing direct setData
  const tickerRef = useRef<string | null>(null);
  useEffect(() => {
    tickerRef.current = selectedTicker;
  });
  const fetchTicker = useCallback(async (ticker: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = `http://localhost:8000/api/intelligence/unified?ticker=${encodeURIComponent(ticker)}&limit=5`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json() as ApiResponse;
      if (tickerRef.current === ticker) {
        setData(json);
      }
    } catch (e: unknown) {
      if (tickerRef.current === ticker) {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      if (tickerRef.current === ticker) {
        setLoading(false);
      }
    }
  }, []);

  // M029 — load market history + options chain when ticker selected
  const fetchMarketData = useCallback(async (ticker: string) => {
    setLoadingMarket(true);
    try {
      const [histRes, optRes] = await Promise.all([
        fetch(`http://localhost:8000/api/market/assets/${encodeURIComponent(ticker)}/history`),
        fetch(`http://localhost:8000/api/options/chain/${encodeURIComponent(ticker)}`),
      ]);
      if (tickerRef.current === ticker) {
        if (histRes.ok) setHistoryData(await histRes.json() as AssetHistoryData);
        if (optRes.ok) setOptionsChain(await optRes.json() as OptionsChainData);
      }
    } catch {
      // non-blocking — market data is enhancement, not critical
    } finally {
      if (tickerRef.current === ticker) setLoadingMarket(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (selectedTicker) {
        fetchTicker(selectedTicker);
        fetchMarketData(selectedTicker);
      } else {
        setData(null);
        setHistoryData(null);
        setOptionsChain(null);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [selectedTicker, fetchTicker, fetchMarketData]);

  const isOpen = selectedTicker !== null;

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="add-backdrop"
          onClick={closeDrawer}
        />
      )}

      {/* Drawer panel */}
      <div className={`add-drawer ${isOpen ? "add-drawer--open" : ""}`}>
        {/* Header */}
        <div className="add-header">
          <div className="add-ticker-row">
            <div className="add-ticker">{selectedTicker ?? "—"}</div>
            {data && (
              <span className={`badge ${directionBadge(
                data.watchlist?.items?.[0]?.direction ??
                data.quant_signals?.ranking?.[0]?.direction ??
                data.conviction?.positions?.[0]?.signal_type ??
                ""
              )}`}>
                {directionLabel(
                  data.watchlist?.items?.[0]?.direction ??
                  data.quant_signals?.ranking?.[0]?.direction ??
                  data.conviction?.positions?.[0]?.signal_type ??
                  ""
                )}
              </span>
            )}
          </div>
          <button className="add-close" onClick={closeDrawer} aria-label="Fechar">
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="add-body">
          {loading && (
            <div className="add-loading">
              <div className="add-spinner" />
              <span>Carregando dados de {selectedTicker}...</span>
            </div>
          )}

          {error && (
            <div className="add-error">
              <span>⚠ Erro: {error}</span>
              <button className="btn secondary" onClick={() => selectedTicker && fetchTicker(selectedTicker)}>Tentar novamente</button>
            </div>
          )}

          {data && !loading && (
            <div className="add-content">
              {/* M029 — Tab navigation */}
              <div className="add-tabs">
                <button
                  className={`add-tab ${activeTab === "visao_geral" ? "add-tab--active" : ""}`}
                  onClick={() => setActiveTab("visao_geral")}
                >
                  Visão Geral
                </button>
                <button
                  className={`add-tab ${activeTab === "historico" ? "add-tab--active" : ""}`}
                  onClick={() => setActiveTab("historico")}
                >
                  Histórico
                  {loadingMarket && <span className="add-tab-spinner" />}
                </button>
                <button
                  className={`add-tab ${activeTab === "opcoes" ? "add-tab--active" : ""}`}
                  onClick={() => setActiveTab("opcoes")}
                >
                  Opções
                  {optionsChain && <span className="add-tab-badge">{optionsChain.total_options}</span>}
                </button>
              </div>

              {/* ── TAB: VISÃO GERAL ── */}
              {activeTab === "visao_geral" && (
              <>
              <div className="add-header-block">
                <div className="add-hb-row">
                  <div className="add-hb-item">
                    <span className="add-hb-label">Score</span>
                    <span className="add-hb-val" style={{ color: scoreColor(
                      data.watchlist?.items?.[0]?.score ??
                      data.quant_signals?.ranking?.[0]?.score_final ??
                      data.signal_matrix?.assets?.[0]?.score_agregado ??
                      data.valuation?.summary?.[0]?.integrated_score ??
                      null
                    ) }}>
                      {unavailable(
                        data.watchlist?.items?.[0]?.score ??
                        data.quant_signals?.ranking?.[0]?.score_final ??
                        data.signal_matrix?.assets?.[0]?.score_agregado ??
                        data.valuation?.summary?.[0]?.integrated_score ??
                        null
                      )}
                    </span>
                  </div>
                  {data.watchlist?.items?.[0]?.price != null && (
                    <div className="add-hb-item">
                      <span className="add-hb-label">Preço</span>
                      <span className="add-hb-val">R$ {typeof data.watchlist.items[0].price === "number" ? data.watchlist.items[0].price.toFixed(2) : "—"}</span>
                    </div>
                  )}
                  {data.watchlist?.items?.[0]?.variacao_pct != null && (
                    <div className="add-hb-item">
                      <span className="add-hb-label">Variação</span>
                      <span className="add-hb-val" style={{ color: (data.watchlist.items[0].variacao_pct ?? 0) >= 0 ? "var(--pos)" : "var(--neg)" }}>
                        {(data.watchlist.items[0].variacao_pct ?? 0) >= 0 ? "+" : ""}
                        {data.watchlist.items[0].variacao_pct != null && typeof data.watchlist.items[0].variacao_pct === "number" ? data.watchlist.items[0].variacao_pct.toFixed(2) : "—"}%
                      </span>
                    </div>
                  )}
                  <div className="add-hb-item">
                    <span className="add-hb-label">Direção</span>
                    <span className="add-hb-val">{directionLabel(data.watchlist?.items?.[0]?.direction ?? "—")}</span>
                  </div>
                  <div className="add-hb-item">
                    <span className="add-hb-label">Status</span>
                    <span className="add-hb-val">{unavailable(data.watchlist?.items?.[0]?.status ?? data.valuation?.summary?.[0]?.integrated_status)}</span>
                  </div>
                </div>
                <div className="add-hb-row">
                  <div className="add-hb-item">
                    <span className="add-hb-label">Upside</span>
                    <span className="add-hb-val" style={{ color: (data.valuation?.summary?.[0]?.upside_pct ?? 0) >= 0 ? "var(--pos)" : "var(--neg)" }}>
                      {data.valuation?.summary?.[0]?.upside_pct != null
                        ? `${(data.valuation.summary[0].upside_pct ?? 0) >= 0 ? "+" : ""}${(typeof data.valuation.summary[0].upside_pct === "number" ? data.valuation.summary[0].upside_pct.toFixed(1) : "—")}%`
                        : "—"}
                    </span>
                  </div>
                  <div className="add-hb-item">
                    <span className="add-hb-label">Setor</span>
                    <span className="add-hb-val">{unavailable(data.watchlist?.items?.[0]?.sector)}</span>
                  </div>
                  <div className="add-hb-item">
                    <span className="add-hb-label">Governança</span>
                    <span className="add-hb-val">
                      {data.watchlist?.items?.[0]?.governance_blocked
                        ? "🔴 BLOQUEADO"
                        : "🟢 OK"}
                    </span>
                  </div>
                  <div className="add-hb-item">
                    <span className="add-hb-label">Última att</span>
                    <span className="add-hb-val">{timeAgo(data.watchlist?.items?.[0]?.updated_at ?? data.timestamp)}</span>
                  </div>
                </div>
              </div>

              {/* ── TÉCNICO ── */}
              <BlockSection label="Técnico" status={data.signal_matrix?.assets?.[0]?.blocos?.tecnico_indicadores?.status}>
                {(data.signal_matrix?.assets?.[0]?.blocos?.tecnico_indicadores) && (
                  <div className="add-block-grid">
                    <MetaRow label="Score técnico" value={fmtLocal(data.signal_matrix.assets[0].blocos.tecnico_indicadores.score)} />
                    <MetaRow label="Status" value={unavailable(data.signal_matrix.assets[0].blocos.tecnico_indicadores.technical_status)} />
                    <MetaRow label="Momentum" value={fmtLocal(data.signal_matrix.assets[0].blocos.tecnico_indicadores.momentum_score)} />
                    <MetaRow label="Tendência" value={fmtLocal(data.signal_matrix.assets[0].blocos.tecnico_indicadores.trend_score)} />
                    <MetaRow label="Volatilidade" value={fmtLocal(data.signal_matrix.assets[0].blocos.tecnico_indicadores.volatilidade)} />
                    <MetaRow label="Volume" value={fmtLocal(data.signal_matrix.assets[0].blocos.tecnico_indicadores.volume_score)} />
                    <MetaRow label="Breakout" value={fmtLocal(data.signal_matrix.assets[0].blocos.tecnico_indicadores.breakout_score)} />
                    <MetaRow label="Sup/Res" value={fmtLocal(data.signal_matrix.assets[0].blocos.tecnico_indicadores.support_resistance_score)} />
                    <MetaRow label="Volume 21d" value={
                      data.quant_signals?.ranking?.[0]?.volume_21d != null
                        ? `${(typeof data.quant_signals.ranking[0].volume_21d === "number" ? (data.quant_signals.ranking[0].volume_21d! / 1e6).toFixed(1) : "—")}M`
                        : "—"
                    } />
                    <MetaRow label="Negócios 21d" value={
                      data.quant_signals?.ranking?.[0]?.negocios_21d != null
                        ? `${(typeof data.quant_signals.ranking[0].negocios_21d === "number" ? (data.quant_signals.ranking[0].negocios_21d! / 1e3).toFixed(1) : "—")}k`
                        : "—"
                    } />
                    <MetaRow label="Gatilho" value={unavailable(data.quant_signals?.ranking?.[0]?.gatilho)} />
                    <MetaRow label="Bloqueios" value={unavailable(data.quant_signals?.ranking?.[0]?.risco)} />
                    <MetaRow label="Próxima ação" value={unavailable(data.watchlist?.items?.[0]?.next_action?.replace(/_/g, " "))} />
                    <MetaRow label="Fonte" value={unavailable(data.signal_matrix?.assets?.[0]?.blocos?.tecnico_indicadores?.fonte)} />
                  </div>
                )}
              </BlockSection>

              {/* ── MOMENTUM ── */}
              <BlockSection label="Momentum" status={data.signal_matrix?.assets?.[0]?.blocos?.momentum?.status}>
                {data.signal_matrix?.assets?.[0]?.blocos?.momentum && (
                  <div className="add-block-grid">
                    <MetaRow label="Score" value={fmtLocal(data.signal_matrix.assets[0].blocos.momentum.score)} />
                    <MetaRow label="Regime" value={unavailable(data.signal_matrix.assets[0].blocos.momentum.regime)} />
                    <MetaRow label="Tendência" value={unavailable(data.signal_matrix.assets[0].blocos.momentum.tendencia)} />
                    <MetaRow label="Evidência" value={unavailable(data.signal_matrix.assets[0].blocos.momentum.evidencia)} />
                    <MetaRow label="Fonte" value={unavailable(data.signal_matrix.assets[0].blocos.momentum.fonte)} />
                  </div>
                )}
              </BlockSection>

              {/* ── LIQUIDEZ ── */}
              <BlockSection label="Liquidez" status={data.signal_matrix?.assets?.[0]?.blocos?.liquidez?.status}>
                {data.signal_matrix?.assets?.[0]?.blocos?.liquidez && (
                  <div className="add-block-grid">
                    <MetaRow label="Score" value={fmtLocal(data.signal_matrix.assets[0].blocos.liquidez.score)} />
                    <MetaRow label="Evidência" value={unavailable(data.signal_matrix.assets[0].blocos.liquidez.evidencia)} />
                    <MetaRow label="ADV 21d" value={
                      data.watchlist?.items?.[0]?.adv_21d != null
                        ? `R$ ${(typeof data.watchlist.items[0].adv_21d === "number" ? (data.watchlist.items[0].adv_21d! / 1e6).toFixed(1) : "—")}M`
                        : "—"
                    } />
                    <MetaRow label="Liq. score" value={fmtLocal(data.watchlist?.items?.[0]?.liquidity)} />
                  </div>
                )}
              </BlockSection>

              {/* ── MACRO ── */}
              <BlockSection label="Macro" status={data.macro?.status}>
                {data.macro && (
                  <div className="add-block-grid">
                    <MetaRow label="Regime" value={unavailable(data.macro.regime?.regime)} />
                    <MetaRow label="Descrição" value={unavailable(data.macro.regime?.description)} />
                    <MetaRow label="Selic" value={fmtLocal(data.macro.current_values?.selic_meta, "%")} />
                    <MetaRow label="IPCA 12m" value={fmtLocal(data.macro.current_values?.ipca_12m, "%")} />
                    <MetaRow label="PTAX" value={fmtLocal(data.macro.current_values?.ptax)} />
                    <MetaRow label="PTAX tendência" value={fmtLocal(data.macro.current_values?.ptax_trend_pct, "%")} />
                    {(data.macro.sector_impact ?? []).length > 0 && (
                      <div className="add-meta-row">
                        <span className="add-meta-key">Impacto setorial</span>
                          <span className="add-meta-val">{data.macro.sector_impact?.map((s) => `${s.sector}: ${s.impact}`).join(" | ")}</span>
                        </div>
                    )}
                  </div>
                )}
              </BlockSection>

              {/* ── OPÇÕES ── */}
              <BlockSection label="Opções" status={data.signal_matrix?.assets?.[0]?.blocos?.opcoes?.status}>
                {data.signal_matrix?.assets?.[0]?.blocos?.opcoes && (
                  <div className="add-block-grid">
                    <MetaRow label="Estrutura" value={unavailable(data.signal_matrix.assets[0].blocos.opcoes.estrutura)} />
                    <MetaRow label="IV Rank" value={fmtLocal(data.signal_matrix.assets[0].blocos.opcoes.iv_rank)} />
                    <MetaRow label="Payoff" value={unavailable(data.signal_matrix.assets[0].blocos.opcoes.payoff)} />
                    <MetaRow label="Liq. opções" value={fmtLocal(data.signal_matrix.assets[0].blocos.opcoes.liquidez)} />
                    <MetaRow label="Evidência" value={unavailable(data.signal_matrix.assets[0].blocos.opcoes.evidencia)} />
                    <MetaRow label="Fonte" value={unavailable(data.signal_matrix.assets[0].blocos.opcoes.fonte)} />
                    <MetaRow label="Tem opções" value={data.watchlist?.items?.[0]?.has_options ? "Sim" : "Não"} />
                  </div>
                )}
              </BlockSection>

              {/* ── VALUATION ── */}
              <BlockSection label="Valuation" status={data.signal_matrix?.assets?.[0]?.blocos?.valuation?.status}>
                {data.signal_matrix?.assets?.[0]?.blocos?.valuation && (
                  <div className="add-block-grid">
                    <MetaRow label="Fair Value" value={fmtLocal(data.signal_matrix.assets[0].blocos.valuation.fair_value)} />
                    <MetaRow label="Preço atual" value={fmtLocal(data.signal_matrix.assets[0].blocos.valuation.preco)} />
                    <MetaRow label="Upside" value={fmtLocal(data.signal_matrix.assets[0].blocos.valuation.upside_pct, "%")} />
                    <MetaRow label="Método" value={unavailable(data.signal_matrix.assets[0].blocos.valuation.metodo)} />
                    <MetaRow label="Status sanidade" value={unavailable(data.signal_matrix.assets[0].blocos.valuation.risk_status)} />
                    <MetaRow label="Tem valuation" value={data.watchlist?.items?.[0]?.has_valuation ? "Sim" : "Não"} />
                  </div>
                )}
              </BlockSection>

              {/* ── CONVICÇÃO ── */}
              <BlockSection label="Convicção" status={data.conviction?.status}>
                {(data.conviction?.positions ?? []).length > 0 && (
                  <div className="add-block-grid">
                    <MetaRow label="Score" value={fmtLocal(data.conviction!.positions![0].score)} />
                    <MetaRow label="Nível" value={unavailable(data.conviction!.positions![0].conviction_level)} />
                    <MetaRow label="Mudança" value={
                      data.conviction!.positions![0].change != null
                        ? `${data.conviction!.positions![0].change! > 0 ? "+" : ""}${data.conviction!.positions![0].change}`
                        : "—"
                    } />
                    <MetaRow label="De → Para" value={
                      data.conviction!.positions![0].from_score != null && data.conviction!.positions![0].to_score != null
                        ? `${(typeof data.conviction!.positions![0].from_score === "number" ? data.conviction!.positions![0].from_score!.toFixed(1) : "—")} → ${(typeof data.conviction!.positions![0].to_score === "number" ? data.conviction!.positions![0].to_score!.toFixed(1) : "—")}`
                        : "—"
                    } />
                    <MetaRow label="Rationale" value={unavailable(data.conviction!.positions![0].rationale)} />
                    <MetaRow label="Tipo sinal" value={unavailable(data.conviction!.positions![0].signal_type)} />
                    <MetaRow label="Histórico" value={data.conviction!.positions![0].has_history ? "Sim" : "Não"} />
                  </div>
                )}
              </BlockSection>

              {/* ── TESE ── */}
              <BlockSection label="Tese" status={data.thesis?.status}>
                {(data.thesis?.theses ?? []).length > 0 && (
                  <div className="add-block-grid">
                    <MetaRow label="Sentimento" value={unavailable(data.thesis!.theses![0].sentiment)} />
                    <MetaRow label="Score" value={fmtLocal(data.thesis!.theses![0].conviction_score)} />
                    <MetaRow label="Hipótese" value={unavailable(data.thesis!.theses![0].hipotese_principal)} />
                    {(data.thesis!.theses![0].tese_bullish ?? []).length > 0 && (
                      <div className="add-meta-row">
                        <span className="add-meta-key">Bull case</span>
                          <span className="add-meta-val" style={{ fontSize: "0.7rem" }}>
                            {data.thesis!.theses![0].tese_bullish?.map((b) => `• ${b.text}`).join(" ")}
                          </span>
                        </div>
                    )}
                    {(data.thesis!.theses![0].tese_bearish ?? []).length > 0 && (
                      <div className="add-meta-row">
                        <span className="add-meta-key">Bear case</span>
                          <span className="add-meta-val" style={{ fontSize: "0.7rem" }}>
                            {data.thesis!.theses![0].tese_bearish?.map((b) => `• ${b.text}`).join(" ")}
                          </span>
                        </div>
                    )}
                    {(data.thesis!.theses![0].fatores_risco ?? []).length > 0 && (
                      <div className="add-meta-row">
                        <span className="add-meta-key">Riscos</span>
                          <span className="add-meta-val" style={{ fontSize: "0.7rem" }}>
                            {data.thesis!.theses![0].fatores_risco?.map((r) => `⚠ ${r.texto}`).join(" ")}
                          </span>
                        </div>
                    )}
                    <MetaRow label="Price target" value={fmtLocal(data.thesis!.theses![0].price_target)} />
                    <MetaRow label="Fair value" value={fmtLocal(data.thesis!.theses![0].fair_value)} />
                    <MetaRow label="Upside" value={fmtLocal(data.thesis!.theses![0].upside_pct, "%")} />
                    {(data.thesis!.theses![0].indicadores_usados ?? []).length > 0 && (
                      <div className="add-meta-row">
                        <span className="add-meta-key">Indicadores</span>
                        <span className="add-meta-val">
                          {data.thesis!.theses![0].indicadores_usados?.join(", ")}
                        </span>
                      </div>
                    )}
                    {data.thesis!.theses![0].contexto_macro && (
                      <div className="add-meta-row">
                        <span className="add-meta-key">Contexto macro</span>
                          <span className="add-meta-val" style={{ fontSize: "0.68rem" }}>
                            {String(data.thesis!.theses![0].contexto_macro?.regime ?? "—")} / {String(data.thesis!.theses![0].contexto_macro?.tendencia ?? "—")}
                          </span>
                        </div>
                    )}
                  </div>
                )}
              </BlockSection>

              {/* ── CONFLITOS ── */}
              {(data.signal_matrix?.assets?.[0]?.conflitos?.length ?? 0) > 0 && (
                <div className="add-section">
                  <div className="add-section-header">
                    <span className="add-section-label">Conflitos</span>
                    <span className="badge badge-sell">{data.signal_matrix!.assets![0].conflitos!.length}</span>
                  </div>
                  <div className="add-conflicts">
                    {data.signal_matrix?.assets?.[0]?.conflitos?.map((c, i) => (
                      <div key={i} className="add-conflict-item">⚠ {c}</div>
                    ))}
                  </div>
                </div>
              )}
              </>
              )}

              {/* ── TAB: HISTÓRICO DA AÇÃO ── */}
              {activeTab === "historico" && (
              <div className="add-section">
                <div className="add-section-header">
                  <span className="add-section-label">Histórico</span>
                  <span className="badge badge-cyan">RTD snapshot</span>
                </div>
                {loadingMarket && historyData == null && (
                  <div className="add-loading" style={{ padding: "16px 0" }}>
                    <div className="add-spinner" />
                    <span>carregando...</span>
                  </div>
                )}
                {historyData && historyData.status === "ok" && historyData.ohlcv && (
                  <div className="add-block-grid">
                    <MetaRow label="Data" value={unavailable(historyData.ohlcv.date)} />
                    <MetaRow label="Abertura" value={fmtLocal(historyData.ohlcv.open)} />
                    <MetaRow label="Máxima" value={fmtLocal(historyData.ohlcv.high)} />
                    <MetaRow label="Mínima" value={fmtLocal(historyData.ohlcv.low)} />
                    <MetaRow label="Fechamento" value={fmtLocal(historyData.ohlcv.close)} />
                    <MetaRow label="VWAP" value={fmtLocal(historyData.ohlcv.vwap)} />
                    <MetaRow label="Volume" value={
                      historyData.ohlcv.volume != null
                        ? `${(historyData.ohlcv.volume / 1e6).toFixed(1)}M`
                        : "—"
                    } />
                    <MetaRow label="RSI" value={fmtLocal(historyData.indicators?.rsi)} />
                    <MetaRow label="ADX" value={fmtLocal(historyData.indicators?.adx)} />
                    <MetaRow label="MACD" value={fmtLocal(historyData.indicators?.macd)} />
                    <MetaRow label="Bollinger b%" value={fmtLocal(historyData.indicators?.bollinger_b)} />
                    <MetaRow label="HiLo" value={fmtLocal(historyData.indicators?.hilo)} />
                    <MetaRow label="Ret. semana" value={fmtLocal(historyData.summary?.return_semana, "%")} />
                    <MetaRow label="Ret. mês" value={fmtLocal(historyData.summary?.return_mes, "%")} />
                    <MetaRow label="Ret. 3m" value={fmtLocal(historyData.summary?.return_3m, "%")} />
                    <MetaRow label="Ret. YTD" value={fmtLocal(historyData.summary?.return_ytd, "%")} />
                    <MetaRow label="Volatilidade" value={fmtLocal(historyData.indicators?.volatilidade_hist, "%")} />
                    <MetaRow label="Fonte" value={unavailable(historyData.source)} />
                  </div>
                )}
                {!loadingMarket && !historyData && (
                  <div className="add-unavailable">
                    histórico indisponível — requer COTAHIST daily ingestion (M015)
                  </div>
                )}
                {!loadingMarket && historyData && historyData.status !== "ok" && (
                  <div className="add-unavailable">
                    {unavailable(historyData.ohlcv ? "" : "ativo não encontrado no RTD")}
                  </div>
                )}
              </div>
              )}

              {/* ── TAB: OPÇÕES ── */}
              {activeTab === "opcoes" && (
              <div className="add-section">
                <div className="add-section-header">
                  <span className="add-section-label">Opções</span>
                  {optionsChain && optionsChain.total_options > 0 && (
                    <span className="badge badge-buy">
                      {optionsChain.calls_count}C / {optionsChain.puts_count}P
                    </span>
                  )}
                </div>
                {loadingMarket && optionsChain == null && (
                  <div className="add-loading" style={{ padding: "16px 0" }}>
                    <div className="add-spinner" />
                    <span>carregando...</span>
                  </div>
                )}
                {!loadingMarket && optionsChain && optionsChain.total_options > 0 && (
                  <div className="add-block-grid">
                    <MetaRow label="Ativo objeto" value={unavailable(optionsChain.underlying)} />
                    <MetaRow label="Spot" value={optionsChain.spot_price != null ? `R$ ${optionsChain.spot_price}` : "—"} />
                    <MetaRow label="Expiry disponíveis" value={String(optionsChain.expirations.length)} />
                    <MetaRow label="Calls" value={String(optionsChain.calls_count)} />
                    <MetaRow label="Puts" value={String(optionsChain.puts_count)} />
                    <MetaRow label="Total opções" value={String(optionsChain.total_options)} />
                    <MetaRow label="Dados RTD" value={optionsChain.has_live_data ? "Sim" : "Apenas CSVs"} />
                    {optionsChain.expirations.length > 0 && (
                      <div className="add-meta-row">
                        <span className="add-meta-key">Vencimentos</span>
                        <span className="add-meta-val" style={{ fontSize: "0.68rem" }}>
                          {optionsChain.expirations.slice(0, 5).join(", ")}
                          {optionsChain.expirations.length > 5 ? ` +${optionsChain.expirations.length - 5}` : ""}
                        </span>
                      </div>
                    )}
                  </div>
                )}
                {!loadingMarket && optionsChain && optionsChain.total_options === 0 && (
                  <div className="add-unavailable">
                    sem opções disponíveis para {selectedTicker} nas fontes atuais.
                    Adicione o ativo ao scanner de opções ou configure novas expirations.
                  </div>
                )}
                {!loadingMarket && !optionsChain && (
                  <div className="add-unavailable">
                    cadeia de opções indisponível para {selectedTicker}.
                  </div>
                )}
                {!loadingMarket && optionsChain && (optionsChain.calls_count > 0 || optionsChain.puts_count > 0) && (
                  <div style={{ marginTop: "12px" }}>
                    {optionsChain.puts.slice(0, 5).length > 0 && (
                      <>
                        <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "var(--fg-5)", textTransform: "uppercase", marginBottom: "6px" }}>
                          PUTs — primeiro vencimento
                        </div>
                        <div className="add-block-grid">
                          {optionsChain.puts.slice(0, 5).map((opt, idx) => (
                            <MetaRow
                              key={idx}
                              label={unavailable(opt.ticker)}
                              value={`S:${fmtLocal(opt.strike)} DTE:${opt.dte ?? "—"} R$:${fmtLocal(opt.last_price)} ${opt.bid ? `Bid:${fmtLocal(opt.bid)} Ask:${fmtLocal(opt.ask)}` : ""}`}
                            />
                          ))}
                        </div>
                      </>
                    )}
                    {optionsChain.calls.slice(0, 5).length > 0 && (
                      <>
                        <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "var(--fg-5)", textTransform: "uppercase", margin: "12px 0 6px" }}>
                          CALLs — primeiro vencimento
                        </div>
                        <div className="add-block-grid">
                          {optionsChain.calls.slice(0, 5).map((opt, idx) => (
                            <MetaRow
                              key={idx}
                              label={unavailable(opt.ticker)}
                              value={`S:${fmtLocal(opt.strike)} DTE:${opt.dte ?? "—"} R$:${fmtLocal(opt.last_price)} ${opt.bid ? `Bid:${fmtLocal(opt.bid)} Ask:${fmtLocal(opt.ask)}` : ""}`}
                            />
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
              )}

              {/* ── FOOTER: fontes ── */}
              <div className="add-footer">
                <div className="add-footer-row">
                  <span>updated:</span>
                  <span>{timeAgo(data.timestamp)}</span>
                </div>
                <div className="add-footer-row">
                  <span>fontes:</span>
                  <span>
                    {[
                      data.watchlist?.items?.[0]?.source,
                      data.signal_matrix?.assets?.[0]?.blocos?.tecnico_indicadores?.fonte,
                    ].filter(Boolean).join(" | ") || "indisponível"}
                  </span>
                </div>
                {data.errors && data.errors.length > 0 && (
                  <div className="add-footer-row">
                    <span className="add-partial-badge">⚠ dados parciais</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .add-backdrop {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.5);
          z-index: 50;
        }
        .add-drawer {
          position: fixed;
          top: 0;
          right: 0;
          height: 100vh;
          width: min(520px, 95vw);
          background: var(--bg-2);
          border-left: 1px solid var(--border-2);
          z-index: 51;
          display: flex;
          flex-direction: column;
          transform: translateX(100%);
          transition: transform 0.25s ease;
          overflow: hidden;
        }
        .add-drawer--open {
          transform: translateX(0);
        }
        .add-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 20px;
          border-bottom: 1px solid var(--border-2);
          flex-shrink: 0;
        }
        .add-ticker-row {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .add-ticker {
          font-family: var(--font-mono);
          font-size: 1.2rem;
          font-weight: 800;
          color: var(--fg-1);
          letter-spacing: 0.5px;
        }
        .add-close {
          background: none;
          border: none;
          color: var(--fg-5);
          font-size: 1.2rem;
          cursor: pointer;
          padding: 4px 8px;
          border-radius: var(--r-md);
        }
        .add-close:hover { background: var(--bg-3); }
        .add-body {
          flex: 1;
          overflow-y: auto;
          padding: 0;
        }
        .add-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
          padding: 48px 24px;
          color: var(--fg-5);
          font-size: 0.82rem;
        }
        .add-spinner {
          width: 28px;
          height: 28px;
          border: 2px solid var(--border-2);
          border-top-color: var(--brand-400);
          border-radius: 50%;
          animation: addSpin 0.8s linear infinite;
        }
        @keyframes addSpin { to { transform: rotate(360deg); } }
        .add-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 10px;
          padding: 32px 24px;
          color: var(--neg);
          font-size: 0.78rem;
        }
        .add-content {
          display: flex;
          flex-direction: column;
          gap: 0;
          padding-bottom: 24px;
        }
        .add-header-block {
          padding: 16px 20px;
          background: var(--bg-3);
          border-bottom: 1px solid var(--border-2);
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .add-hb-row {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
        }
        .add-hb-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 60px;
        }
        .add-hb-label {
          font-size: 0.58rem;
          font-weight: 700;
          color: var(--fg-6);
          text-transform: uppercase;
          letter-spacing: 0.3px;
        }
        .add-hb-val {
          font-size: 0.85rem;
          font-weight: 700;
          color: var(--fg-2);
          font-family: var(--font-mono);
        }
        .add-section {
          padding: 14px 20px;
          border-bottom: 1px solid var(--border-1);
        }
        .add-section-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 10px;
        }
        .add-section-label {
          font-size: 0.72rem;
          font-weight: 800;
          color: var(--fg-3);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .add-unavailable {
          font-size: 0.7rem;
          color: var(--warn);
          font-style: italic;
        }
        .add-block-grid {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .add-meta-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
        }
        .add-meta-key {
          font-size: 0.62rem;
          color: var(--fg-5);
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.3px;
          flex-shrink: 0;
        }
        .add-meta-val {
          font-size: 0.72rem;
          color: var(--fg-3);
          font-family: var(--font-mono);
          text-align: right;
        }
        .add-conflicts {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .add-conflict-item {
          font-size: 0.7rem;
          color: var(--neg);
          padding: 4px 8px;
          background: rgba(255,107,107,0.06);
          border-radius: var(--r-md);
        }
        .add-footer {
          padding: 12px 20px;
          display: flex;
          flex-direction: column;
          gap: 4px;
          border-top: 1px solid var(--border-1);
          margin-top: 4px;
        }
        .add-footer-row {
          display: flex;
          justify-content: space-between;
          font-size: 0.62rem;
          color: var(--fg-6);
          font-family: var(--font-mono);
        }
        .add-partial-badge {
          color: var(--warn);
          font-weight: 700;
        }
        /* M029 — Tab navigation */
        .add-tabs {
          display: flex;
          border-bottom: 1px solid var(--border-2);
          background: var(--bg-3);
          padding: 0 8px;
          gap: 2px;
        }
        .add-tab {
          background: none;
          border: none;
          padding: 10px 16px;
          font-size: 0.72rem;
          font-weight: 700;
          color: var(--fg-5);
          cursor: pointer;
          border-bottom: 2px solid transparent;
          margin-bottom: -1px;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: color 0.15s, border-color 0.15s;
          text-transform: uppercase;
          letter-spacing: 0.4px;
        }
        .add-tab:hover { color: var(--fg-3); }
        .add-tab--active {
          color: var(--brand-400);
          border-bottom-color: var(--brand-400);
        }
        .add-tab-spinner {
          display: inline-block;
          width: 8px;
          height: 8px;
          border: 1.5px solid var(--border-2);
          border-top-color: var(--brand-400);
          border-radius: 50%;
          animation: addSpin 0.8s linear infinite;
        }
        .add-tab-badge {
          background: var(--pos);
          color: var(--bg-0);
          font-size: 0.6rem;
          font-weight: 800;
          padding: 1px 5px;
          border-radius: 10px;
          line-height: 1.4;
        }
      `}</style>
    </>
  );
}