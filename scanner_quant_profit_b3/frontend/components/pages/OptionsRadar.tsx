"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getOptionsRadar,
  getOptionsChain,
  getOptionHistory,
  type OptionsRadarResponse,
  type OptionsChainResponse,
  type OptionEntry,
  type OptionHistoryResponse,
} from "@/lib/api";
import { fmt } from "@/lib/safeNumber";

// ── Types ────────────────────────────────────────────────────────────────────

interface Filters {
  underlying: string;
  tipo: string;
  status: string;
  minScore: number;
  onlyRTD: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusBadge(status: string): string {
  const s = status?.toUpperCase() ?? "";
  if (s === "CANDIDATA_PROXIMO_PREGAO") return "badge-buy";
  if (s === "MONITORAR_NO_RTD") return "badge-cyan";
  if (s === "AGUARDAR_LIQUIDEZ") return "badge-amber";
  if (s === "NA_RTD") return "badge-neutral";
  if (s.includes("RTD")) return "badge-cyan";
  return "badge-neutral";
}

function statusLabel(status: string): string {
  const s = status?.toUpperCase() ?? "";
  if (s === "CANDIDATA_PROXIMO_PREGAO") return "PRÓXIMO";
  if (s === "MONITORAR_NO_RTD") return "MONITORAR";
  if (s === "AGUARDAR_LIQUIDEZ") return "AGUARDAR";
  if (s === "NA_RTD") return "NO RTD";
  if (s === "RTD_AO_VIVO") return "RTD LIVE";
  if (s === "SEM_BIDASK") return "SEM RTD";
  if (s === "SEM_DADOS_RTD") return "CSV ONLY";
  if (s === "SEM_PRECO") return "SEM PREÇO";
  return s.slice(0, 12) || "—";
}

function tipoColor(tipo: string): string {
  const t = (tipo ?? "").toUpperCase();
  if (t === "CALL") return "var(--pos)";
  if (t === "PUT") return "var(--neg)";
  return "var(--fg-3)";
}

function scoreColor(score: number | null | undefined): string {
  if (score == null) return "var(--fg-5)";
  if (score >= 80) return "var(--pos)";
  if (score >= 50) return "var(--warn)";
  return "var(--neg)";
}

function dteColor(dte: number | null): string {
  if (dte == null) return "var(--fg-5)";
  if (dte <= 7) return "var(--neg)";
  if (dte <= 23) return "var(--warn)";
  return "var(--fg-3)";
}

function unavailable(val: unknown): string {
  if (val == null || val === undefined) return "—";
  return String(val);
}

// ── Option row component ───────────────────────────────────────────────────────

function OptionRow({
  opt,
  onClick,
}: {
  opt: OptionEntry;
  onClick: (opt: OptionEntry) => void;
}) {
  return (
    <div className="opt-row" onClick={() => onClick(opt)} role="button" tabIndex={0}>
      <div className="opt-ticker">{unavailable(opt.ticker)}</div>
      <div className="opt-tipo" style={{ color: tipoColor(opt.option_type) }}>
        {opt.option_type}
      </div>
      <div className="opt-strike">
        <span className="opt-label">Strike</span>
        <span className="opt-value">{fmt(opt.strike)}</span>
      </div>
      <div className="opt-dte" style={{ color: dteColor(opt.dte) }}>
        <span className="opt-label">DTE</span>
        <span className="opt-value">{opt.dte ?? "—"}</span>
      </div>
      <div className="opt-price">
        <span className="opt-label">Prêmio</span>
        <span className="opt-value">{fmt(opt.last_price)}</span>
      </div>
      <div className="opt-bidask">
        <span className="opt-label">Bid/Ask</span>
        <span className="opt-value">
          {opt.bid != null && opt.ask != null
            ? `${fmt(opt.bid)} / ${fmt(opt.ask)}`
            : opt.last_price != null
            ? `R$ ${fmt(opt.last_price)}`
            : "—"}
        </span>
      </div>
      <div className="opt-spread">
        <span className="opt-label">Spread</span>
        <span className="opt-value">{opt.spread_pct != null ? `${fmt(opt.spread_pct)}%` : "—"}</span>
      </div>
      {opt.score != null && (
        <div className="opt-score" style={{ color: scoreColor(opt.score) }}>
          <span className="opt-label">Score</span>
          <span className="opt-value">{opt.score.toFixed(0)}</span>
        </div>
      )}
      {opt.delta != null && (
        <div className="opt-greek">
          <span className="opt-label">Delta</span>
          <span className="opt-value">{String(fmt(opt.delta ?? null))}</span>
        </div>
      )}
      <div className="opt-status">
        <span className={`badge ${statusBadge(opt.status)}`}>
          {statusLabel(opt.status)}
        </span>
      </div>
      {opt.estruturas_sugeridas && (
        <div className="opt-estrategia">{opt.estruturas_sugeridas}</div>
      )}
    </div>
  );
}

// ── Option detail panel ──────────────────────────────────────────────────────

function OptionDetail({
  opt,
  onClose,
}: {
  opt: OptionEntry;
  onClose: () => void;
}) {
  const [history, setHistory] = useState<OptionHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void getOptionHistory(opt.ticker).then(setHistory).catch(() => setHistory(null));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [opt.ticker]);

  return (
    <div className="opt-detail">
      <div className="opt-detail-header">
        <div>
          <span className="opt-detail-ticker">{opt.ticker}</span>
          <span style={{ color: tipoColor(opt.option_type), fontWeight: 700, marginLeft: 8 }}>
            {opt.option_type}
          </span>
          <span style={{ color: "var(--fg-5)", marginLeft: 8 }}>
            Strike {fmt(opt.strike)} | DTE {opt.dte ?? "—"} | Venc {unavailable(opt.expiration_date)}
          </span>
        </div>
        <button className="btn secondary" onClick={onClose}>Fechar</button>
      </div>

      <div className="opt-detail-grid">
        <div className="opt-detail-cell">
          <span className="opt-detail-label">Último preço</span>
          <span className="opt-detail-value">{fmt(opt.last_price)}</span>
        </div>
        <div className="opt-detail-cell">
          <span className="opt-detail-label">Bid</span>
          <span className="opt-detail-value">{fmt(opt.bid)}</span>
        </div>
        <div className="opt-detail-cell">
          <span className="opt-detail-label">Ask</span>
          <span className="opt-detail-value">{fmt(opt.ask)}</span>
        </div>
        <div className="opt-detail-cell">
          <span className="opt-detail-label">Spread</span>
          <span className="opt-detail-value">{opt.spread_pct != null ? `${fmt(opt.spread_pct)}%` : "—"}</span>
        </div>
        {opt.implied_volatility != null && (
          <div className="opt-detail-cell">
            <span className="opt-detail-label">IV</span>
            <span className="opt-detail-value">{String(fmt(opt.implied_volatility ?? null))}</span>
          </div>
        )}
        {opt.delta != null && (
          <div className="opt-detail-cell">
            <span className="opt-detail-label">Delta</span>
            <span className="opt-detail-value">{String(fmt(opt.delta ?? null))}</span>
          </div>
        )}
        {opt.gamma != null && (
          <div className="opt-detail-cell">
            <span className="opt-detail-label">Gama</span>
            <span className="opt-detail-value">{String(fmt(opt.gamma ?? null))}</span>
          </div>
        )}
        {opt.theta != null && (
          <div className="opt-detail-cell">
            <span className="opt-detail-label">Theta</span>
            <span className="opt-detail-value">{String(fmt(opt.theta ?? null))}</span>
          </div>
        )}
        {opt.vega != null && (
          <div className="opt-detail-cell">
            <span className="opt-detail-label">Vega</span>
            <span className="opt-detail-value">{String(fmt(opt.vega ?? null))}</span>
          </div>
        )}
        <div className="opt-detail-cell">
          <span className="opt-detail-label">Moneyness</span>
          <span className="opt-detail-value">{unavailable(opt.moneyness)}</span>
        </div>
        <div className="opt-detail-cell">
          <span className="opt-detail-label">Liq.score</span>
          <span className="opt-detail-value">{fmt(opt.liquidity_score)}</span>
        </div>
      </div>

      {opt.cenario && (
        <div className="opt-detail-section">
          <span className="opt-detail-section-label">Cenário</span>
          <span>{opt.cenario}</span>
        </div>
      )}
      {opt.estruturas_sugeridas && (
        <div className="opt-detail-section">
          <span className="opt-detail-section-label">Estratégia sugerida</span>
          <span>{opt.estruturas_sugeridas}</span>
        </div>
      )}
      {opt.motivo && (
        <div className="opt-detail-section">
          <span className="opt-detail-section-label">Motivo</span>
          <span>{opt.motivo}</span>
        </div>
      )}

      {/* History */}
      <div className="opt-detail-section">
        <span className="opt-detail-section-label">Histórico</span>
        {loading && <span style={{ color: "var(--fg-5)" }}> carregando...</span>}
        {!loading && history && history.status === "ok" && (
          <div className="opt-history-grid">
            <span className="opt-hist-label">Registros</span>
            <span>{history.summary.record_count}</span>
            <span className="opt-hist-label">Último preço</span>
            <span>{fmt(history.summary.current_price)}</span>
            <span className="opt-hist-label">Máxima</span>
            <span>{fmt(history.summary.max_price)}</span>
            <span className="opt-hist-label">Mínima</span>
            <span>{fmt(history.summary.min_price)}</span>
            <span className="opt-hist-label">Média</span>
            <span>{fmt(history.summary.avg_price)}</span>
            <span className="opt-hist-label">Último status</span>
            <span>{unavailable(history.summary.latest_status)}</span>
          </div>
        )}
        {!loading && history && history.status !== "ok" && (
          <span style={{ color: "var(--fg-5)" }}> histórico não disponível</span>
        )}
      </div>

      <div className="opt-detail-source">Fonte: {opt.source}</div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function OptionsRadar() {
  const [radarData, setRadarData] = useState<OptionsRadarResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({
    underlying: "",
    tipo: "",
    status: "",
    minScore: 0,
    onlyRTD: false,
  });
  const [selectedOpt, setSelectedOpt] = useState<OptionEntry | null>(null);
  const [viewMode, setViewMode] = useState<"radar" | "chain">("radar");
  const [chainTarget, setChainTarget] = useState<string>("");
  const [chainData, setChainData] = useState<OptionsChainResponse | null>(null);
  const [loadingChain, setLoadingChain] = useState(false);

  const loadRadar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getOptionsRadar(filters.underlying || undefined);
      setRadarData(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [filters.underlying]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadRadar();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadRadar]);

  const loadChain = useCallback(async (underlying: string) => {
    setLoadingChain(true);
    setChainData(null);
    try {
      const data = await getOptionsChain(underlying);
      setChainData(data);
    } catch {
      setChainData(null);
    } finally {
      setLoadingChain(false);
    }
  }, []);

  // Filter options
  const filteredCandidates = radarData
    ? radarData.candidates_next_session.filter((opt) => {
        if (filters.tipo && opt.option_type !== filters.tipo) return false;
        if (filters.status && opt.status !== filters.status) return false;
        if (filters.minScore > 0 && (opt.score == null || opt.score < filters.minScore)) return false;
        if (filters.onlyRTD && !opt.bid) return false;
        return true;
      })
    : [];

  const filteredMonitor = radarData
    ? radarData.monitor_rtd.filter((opt) => {
        if (filters.tipo && opt.option_type !== filters.tipo) return false;
        if (filters.status && opt.status !== filters.status) return false;
        if (filters.minScore > 0 && (opt.score == null || opt.score < filters.minScore)) return false;
        return true;
      })
    : [];

  // Underlyings available
  const underlyings = radarData ? Object.keys(radarData.by_underlying || {}) : [];

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Options Radar</h1>
          <p className="page-subtitle">
            {loading ? "Carregando..." : radarData ? `${radarData.total.toLocaleString()} opções` : "—"}
            {radarData && (
              <span style={{ marginLeft: 16 }}>
                <span className="badge badge-buy" style={{ marginRight: 4 }}>
                  {radarData.total_candidates}
                </span>
                candidatas
                <span className="badge badge-cyan" style={{ marginLeft: 8, marginRight: 4 }}>
                  {radarData.total_monitor_rtd}
                </span>
                monitorar
              </span>
            )}
          </p>
        </div>
        <div className="page-header-actions">
          <button
            className={`btn ${viewMode === "radar" ? "primary" : "secondary"}`}
            onClick={() => setViewMode("radar")}
          >
            Radar
          </button>
          <button
            className={`btn ${viewMode === "chain" ? "primary" : "secondary"}`}
            onClick={() => setViewMode("chain")}
          >
            Cadeia
          </button>
        </div>
      </div>

      {/* Mode: Chain */}
      {viewMode === "chain" && (
        <div className="or-chain-section">
          <div className="or-chain-input">
            <label>Ativo objeto</label>
            <input
              type="text"
              value={chainTarget}
              onChange={(e) => setChainTarget(e.target.value.toUpperCase())}
              placeholder="Ex: PETR4, PETR, ENEV3"
              style={{ width: 200 }}
            />
            <button
              className="btn primary"
              onClick={() => chainTarget && loadChain(chainTarget)}
              disabled={!chainTarget}
            >
              Buscar
            </button>
          </div>
          {loadingChain && <span style={{ color: "var(--fg-5)" }}> carregando...</span>}
          {!loadingChain && chainData && chainData.status === "ok" && (
            <div className="or-chain-result">
              <div className="or-chain-summary">
                <span className="or-chain-label">{chainData.underlying}</span>
                <span>Spot: {chainData.spot_price != null ? `R$ ${chainData.spot_price}` : "—"}</span>
                <span>
                  <span className="badge badge-buy" style={{ marginRight: 4 }}>
                    {chainData.calls_count}
                  </span>
                  CALLs
                </span>
                <span>
                  <span className="badge badge-sell" style={{ marginRight: 4 }}>
                    {chainData.puts_count}
                  </span>
                  PUTs
                </span>
                <span>{chainData.expirations.length} vencimentos</span>
                <span>RTD: {chainData.has_live_data ? "Sim" : "CSV only"}</span>
              </div>
              {chainData.expirations.length > 0 && (
                <div className="or-chain-expirations">
                  {chainData.expirations.slice(0, 6).map((exp) => (
                    <span key={exp} className="badge badge-neutral">{exp}</span>
                  ))}
                </div>
              )}
              <div className="or-chain-tables">
                {chainData.puts.length > 0 && (
                  <div>
                    <div className="or-chain-table-label">PUTs</div>
                    <div className="or-chain-table-header">
                      <span>Ticker</span><span>Tipo</span><span>Strike</span><span>DTE</span><span>Prêmio</span><span>Bid</span><span>Ask</span><span>Spread</span><span>Delta</span><span>Status</span>
                    </div>
                    {chainData.puts.slice(0, 10).map((opt, i) => (
                      <div key={i} className="or-chain-table-row" onClick={() => setSelectedOpt(opt)} role="button">
                        <span>{opt.ticker}</span>
                        <span style={{ color: "var(--neg)" }}>PUT</span>
                        <span>{fmt(opt.strike)}</span>
                        <span>{opt.dte ?? "—"}</span>
                        <span>{fmt(opt.last_price)}</span>
                        <span>{fmt(opt.bid)}</span>
                        <span>{fmt(opt.ask)}</span>
                        <span>{opt.spread_pct != null ? `${fmt(opt.spread_pct)}%` : "—"}</span>
                        <span>{fmt(opt.delta)}</span>
                        <span className={`badge ${statusBadge(opt.status)}`}>{statusLabel(opt.status)}</span>
                      </div>
                    ))}
                  </div>
                )}
                {chainData.calls.length > 0 && (
                  <div>
                    <div className="or-chain-table-label">CALLs</div>
                    <div className="or-chain-table-header">
                      <span>Ticker</span><span>Tipo</span><span>Strike</span><span>DTE</span><span>Prêmio</span><span>Bid</span><span>Ask</span><span>Spread</span><span>Delta</span><span>Status</span>
                    </div>
                    {chainData.calls.slice(0, 10).map((opt, i) => (
                      <div key={i} className="or-chain-table-row" onClick={() => setSelectedOpt(opt)} role="button">
                        <span>{opt.ticker}</span>
                        <span style={{ color: "var(--pos)" }}>CALL</span>
                        <span>{fmt(opt.strike)}</span>
                        <span>{opt.dte ?? "—"}</span>
                        <span>{fmt(opt.last_price)}</span>
                        <span>{fmt(opt.bid)}</span>
                        <span>{fmt(opt.ask)}</span>
                        <span>{opt.spread_pct != null ? `${fmt(opt.spread_pct)}%` : "—"}</span>
                        <span>{fmt(opt.delta)}</span>
                        <span className={`badge ${statusBadge(opt.status)}`}>{statusLabel(opt.status)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mode: Radar */}
      {viewMode === "radar" && (
        <>
          {/* Filters */}
          <div className="or-filters">
            <div className="or-filter-group">
              <label>Ativo</label>
              <select
                value={filters.underlying}
                onChange={(e) => setFilters({ ...filters, underlying: e.target.value })}
              >
                <option value="">Todos</option>
                {underlyings.map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
            </div>
            <div className="or-filter-group">
              <label>Tipo</label>
              <select
                value={filters.tipo}
                onChange={(e) => setFilters({ ...filters, tipo: e.target.value })}
              >
                <option value="">Todos</option>
                <option value="CALL">CALL</option>
                <option value="PUT">PUT</option>
              </select>
            </div>
            <div className="or-filter-group">
              <label>Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="">Todos</option>
                <option value="CANDIDATA_PROXIMO_PREGAO">Próximo pregão</option>
                <option value="MONITORAR_NO_RTD">Monitorar RTD</option>
                <option value="AGUARDAR_LIQUIDEZ">Aguardar liquidez</option>
                <option value="RTD_AO_VIVO">RTD ao vivo</option>
              </select>
            </div>
            <div className="or-filter-group">
              <label>Score min</label>
              <input
                type="number"
                min={0}
                max={100}
                value={filters.minScore}
                onChange={(e) => setFilters({ ...filters, minScore: Number(e.target.value)})}
                style={{ width: 80 }}
              />
            </div>
            <div className="or-filter-group">
              <label>
                <input
                  type="checkbox"
                  checked={filters.onlyRTD}
                  onChange={(e) => setFilters({ ...filters, onlyRTD: e.target.checked })}
                />
                Só RTD
              </label>
            </div>
            <button className="btn secondary" onClick={loadRadar}>Atualizar</button>
          </div>

          {/* Status summary */}
          {radarData && radarData.by_status && (
            <div className="or-status-bar">
              {Object.entries(radarData.by_status).map(([status, count]) => (
                <div key={status} className="or-status-item">
                  <span className={`badge ${statusBadge(status)}`}>{count.toLocaleString()}</span>
                  <span>{statusLabel(status)}</span>
                </div>
              ))}
            </div>
          )}

          {/* By underlying */}
          {radarData && !filters.underlying && (
            <div className="or-underlyings">
              <div className="or-section-title">Por ativo objeto</div>
              <div className="or-underlyings-grid">
                {Object.entries(radarData.by_underlying || {}).map(([u, data]) => (
                  <div
                    key={u}
                    className="or-underlying-card"
                    onClick={() => setFilters({ ...filters, underlying: u })}
                    role="button"
                  >
                    <div className="or-underlying-name">{u}</div>
                    <div className="or-underlying-stats">
                      <span className="badge badge-buy">{data.calls}</span>
                      <span className="badge badge-sell">{data.puts}</span>
                      <span style={{ color: "var(--fg-5)" }}>total: {data.total}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Candidates */}
          <div className="or-section">
            <div className="or-section-header">
              <span className="or-section-title">
                Candidatas próximo pregão
                <span className="badge badge-buy" style={{ marginLeft: 8 }}>
                  {filteredCandidates.length.toLocaleString()}
                </span>
              </span>
            </div>
            <div className="or-table-header">
              <span>Ticker</span><span>Tipo</span><span>Strike</span><span>DTE</span><span>Prêmio</span><span>Bid/Ask</span><span>Spread</span><span>Score</span><span>Delta</span><span>Status</span>
            </div>
            {loading && <div className="or-loading"><div className="spinner" /><span>carregando...</span></div>}
            {error && <div className="or-error">⚠ {error}</div>}
            {!loading && !error && filteredCandidates.slice(0, 50).map((opt, i) => (
              <OptionRow key={i} opt={opt} onClick={setSelectedOpt} />
            ))}
            {filteredCandidates.length > 50 && (
              <div className="or-more">+ {filteredCandidates.length - 50} opções (use filtros)</div>
            )}
          </div>

          {/* Monitor RTD */}
          <div className="or-section">
            <div className="or-section-header">
              <span className="or-section-title">
                Monitorar no RTD
                <span className="badge badge-cyan" style={{ marginLeft: 8 }}>
                  {filteredMonitor.length.toLocaleString()}
                </span>
              </span>
            </div>
            <div className="or-table-header">
              <span>Ticker</span><span>Tipo</span><span>Strike</span><span>DTE</span><span>Prêmio</span><span>Score</span><span>Status</span>
            </div>
            {!loading && filteredMonitor.slice(0, 30).map((opt, i) => (
              <OptionRow key={i} opt={opt} onClick={setSelectedOpt} />
            ))}
          </div>
        </>
      )}

      {/* Detail panel */}
      {selectedOpt && (
        <div className="or-detail-overlay" onClick={() => setSelectedOpt(null)}>
          <div className="or-detail-panel" onClick={(e) => e.stopPropagation()}>
            <OptionDetail opt={selectedOpt} onClose={() => setSelectedOpt(null)} />
          </div>
        </div>
      )}

      {/* Diagnostic */}
      {radarData && (
        <div className="or-diagnostic">
          <span>fontes: options CSVs</span>
          <span>dados: snapshots pontuais</span>
          <span>total raw: {String(radarData.diagnostic?.["total_raw_records"] ?? "?")}</span>
          <span>timestamp: {radarData.timestamp?.slice(0, 19)}</span>
        </div>
      )}

      <style>{`
        .page-container {
          padding: 20px 24px;
          display: flex;
          flex-direction: column;
          gap: 20px;
          min-height: 100%;
        }
        .page-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
        }
        .page-title {
          font-size: 1.4rem;
          font-weight: 800;
          color: var(--fg-1);
          margin: 0 0 4px;
        }
        .page-subtitle {
          font-size: 0.78rem;
          color: var(--fg-5);
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .page-header-actions { display: flex; gap: 8px; }
        .btn {
          padding: 6px 14px;
          border-radius: var(--r-md);
          font-size: 0.72rem;
          font-weight: 700;
          cursor: pointer;
          border: 1px solid var(--border-2);
          text-transform: uppercase;
          letter-spacing: 0.3px;
        }
        .btn.primary {
          background: var(--brand-500);
          color: white;
          border-color: var(--brand-500);
        }
        .btn.secondary {
          background: var(--bg-3);
          color: var(--fg-3);
        }
        /* Filters */
        .or-filters {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
          align-items: center;
          background: var(--bg-3);
          padding: 12px 16px;
          border-radius: var(--r-lg);
        }
        .or-filter-group {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .or-filter-group label {
          font-size: 0.68rem;
          color: var(--fg-5);
          font-weight: 600;
        }
        .or-filter-group select,
        .or-filter-group input[type=text],
        .or-filter-group input[type=number] {
          padding: 4px 8px;
          background: var(--bg-2);
          border: 1px solid var(--border-2);
          border-radius: var(--r-md);
          color: var(--fg-2);
          font-size: 0.72rem;
        }
        /* Status bar */
        .or-status-bar {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
        }
        .or-status-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.72rem;
          color: var(--fg-5);
        }
        /* Underlyings */
        .or-underlyings { }
        .or-underlyings-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          gap: 8px;
        }
        .or-underlying-card {
          background: var(--bg-3);
          border: 1px solid var(--border-2);
          border-radius: var(--r-md);
          padding: 10px 12px;
          cursor: pointer;
        }
        .or-underlying-card:hover { border-color: var(--brand-500); }
        .or-underlying-name { font-size: 0.8rem; font-weight: 700; color: var(--fg-2); }
        .or-underlying-stats { display: flex; gap: 6px; align-items: center; margin-top: 6px; font-size: 0.65rem; }
        /* Section */
        .or-section { }
        .or-section-title {
          font-size: 0.72rem;
          font-weight: 800;
          color: var(--fg-4);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .or-section-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 0;
          border-bottom: 1px solid var(--border-2);
          margin-bottom: 4px;
        }
        .or-table-header {
          display: grid;
          grid-template-columns: 100px 50px 70px 40px 60px 90px 60px 50px 50px 80px;
          gap: 8px;
          padding: 4px 8px;
          font-size: 0.62rem;
          font-weight: 700;
          color: var(--fg-6);
          text-transform: uppercase;
          border-bottom: 1px solid var(--border-1);
        }
        .or-row-header {
          display: grid;
          grid-template-columns: 100px 50px 70px 40px 60px 90px 60px 50px 50px 80px;
          gap: 8px;
          padding: 4px 8px;
          font-size: 0.62rem;
          color: var(--fg-6);
          font-weight: 700;
          text-transform: uppercase;
          border-bottom: 1px solid var(--border-1);
        }
        /* Option row */
        .opt-row {
          display: grid;
          grid-template-columns: 100px 50px 70px 40px 60px 90px 60px 50px 50px 80px;
          gap: 8px;
          padding: 6px 8px;
          font-size: 0.72rem;
          border-bottom: 1px solid var(--border-1);
          cursor: pointer;
          align-items: center;
        }
        .opt-row:hover { background: var(--bg-3); }
        .opt-ticker { font-family: var(--font-mono); font-weight: 700; color: var(--fg-2); font-size: 0.7rem; }
        .opt-tipo { font-weight: 800; font-size: 0.65rem; }
        .opt-label { font-size: 0.55rem; color: var(--fg-6); display: block; }
        .opt-value { font-size: 0.72rem; font-family: var(--font-mono); }
        .opt-estrategia { font-size: 0.6rem; color: var(--fg-5); grid-column: span 10; padding-top: 2px; }
        /* Table rows for chain */
        .or-chain-section { padding: 0; }
        .or-chain-input { display: flex; align-items: center; gap: 10px; }
        .or-chain-input label { font-size: 0.72rem; font-weight: 700; color: var(--fg-4); }
        .or-chain-result { margin-top: 12px; }
        .or-chain-summary { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; padding: 8px 12px; background: var(--bg-3); border-radius: var(--r-md); margin-bottom: 8px; }
        .or-chain-label { font-size: 1rem; font-weight: 800; color: var(--fg-1); }
        .or-chain-expirations { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
        .or-chain-table-label { font-size: 0.65rem; font-weight: 800; color: var(--fg-5); text-transform: uppercase; margin: 8px 0 4px; }
        .or-chain-table-header { display: grid; grid-template-columns: 90px 40px 60px 40px 60px 60px 60px 50px 50px 80px; gap: 6px; padding: 4px 8px; font-size: 0.6rem; font-weight: 700; color: var(--fg-6); text-transform: uppercase; border-bottom: 1px solid var(--border-1); }
        .or-chain-table-row { display: grid; grid-template-columns: 90px 40px 60px 40px 60px 60px 60px 50px 50px 80px; gap: 6px; padding: 5px 8px; font-size: 0.7rem; border-bottom: 1px solid var(--border-1); cursor: pointer; align-items: center; }
        .or-chain-table-row:hover { background: var(--bg-3); }
        /* Loading/error */
        .or-loading { display: flex; align-items: center; gap: 10px; padding: 16px; color: var(--fg-5); font-size: 0.78rem; }
        .or-error { color: var(--neg); font-size: 0.78rem; padding: 12px; }
        .or-more { padding: 8px; color: var(--fg-5); font-size: 0.72rem; text-align: center; border-bottom: 1px solid var(--border-1); }
        /* Detail overlay */
        .or-detail-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.6);
          z-index: 60;
          display: flex;
          justify-content: flex-end;
        }
        .or-detail-panel {
          width: min(600px, 95vw);
          background: var(--bg-2);
          border-left: 1px solid var(--border-2);
          height: 100%;
          overflow-y: auto;
          padding: 20px;
        }
        /* Option detail */
        .opt-detail { }
        .opt-detail-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--border-2);
          margin-bottom: 16px;
        }
        .opt-detail-ticker { font-family: var(--font-mono); font-size: 1.1rem; font-weight: 800; color: var(--fg-1); }
        .opt-detail-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 16px; }
        .opt-detail-cell { background: var(--bg-3); padding: 8px; border-radius: var(--r-md); }
        .opt-detail-label { font-size: 0.6rem; color: var(--fg-6); font-weight: 700; text-transform: uppercase; display: block; }
        .opt-detail-value { font-size: 0.82rem; font-family: var(--font-mono); color: var(--fg-2); font-weight: 600; }
        .opt-detail-section { padding: 8px 0; border-top: 1px solid var(--border-1); margin-top: 8px; }
        .opt-detail-section-label { font-size: 0.62rem; font-weight: 700; color: var(--fg-5); text-transform: uppercase; display: block; margin-bottom: 4px; }
        .opt-detail-section span { font-size: 0.72rem; color: var(--fg-3); }
        .opt-detail-source { font-size: 0.6rem; color: var(--fg-6); margin-top: 12px; }
        .opt-history-grid { display: grid; grid-template-columns: auto 1fr; gap: 4px 16px; }
        .opt-hist-label { font-size: 0.65rem; color: var(--fg-5); font-weight: 600; }
        /* Diagnostic */
        .or-diagnostic { font-size: 0.6rem; color: var(--fg-6); display: flex; gap: 16px; font-family: var(--font-mono); border-top: 1px solid var(--border-1); padding-top: 12px; }
        .spinner {
          width: 16px; height: 16px;
          border: 2px solid var(--border-2);
          border-top-color: var(--brand-400);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}