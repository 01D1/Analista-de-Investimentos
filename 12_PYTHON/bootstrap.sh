#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# bootstrap.sh — Popula todos os tickers do zero
#
# Uso:
#   ./bootstrap.sh              # todos os tickers
#   ./bootstrap.sh ITUB4 BBDC4  # tickers específicos
# ─────────────────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

PYTHON=python3
LOG_FILE="logs/bootstrap_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

log() { echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG_FILE"; }

# Tickers a processar
if [ $# -gt 0 ]; then
  TICKERS="$@"
  log "Modo seletivo: $TICKERS"
else
  TICKERS=$($PYTHON -c "from config.settings import settings; print(' '.join(settings.active_tickers))" 2>/dev/null)
  log "Todos os tickers ativos: $TICKERS"
fi

log "=========================================="
log "Bootstrap — Intelligence System"
log "=========================================="

# ── 1. Ingestão ────────────────────────────────────────────────────────────
log ""
log "FASE 1 — Baixando dados da CVM e preços B3..."
for TICKER in $TICKERS; do
  log "  ▶ ingest $TICKER"
  $PYTHON -m src.main ingest --ticker "$TICKER" --doc-types DFP,ITR 2>&1 | tee -a "$LOG_FILE" || log "  ✗ $TICKER falhou na ingestão"
done

# ── 2. Processamento ───────────────────────────────────────────────────────
log ""
log "FASE 2 — Processando dados brutos..."
for TICKER in $TICKERS; do
  log "  ▶ process $TICKER"
  $PYTHON -m src.main process --ticker "$TICKER" 2>&1 | tee -a "$LOG_FILE" || log "  ✗ $TICKER falhou no processamento"
done

# ── 3. Análise ─────────────────────────────────────────────────────────────
log ""
log "FASE 3 — Calculando métricas, risco e valuation..."
for TICKER in $TICKERS; do
  log "  ▶ analyze $TICKER"
  $PYTHON -m src.main analyze --ticker "$TICKER" 2>&1 | tee -a "$LOG_FILE" || log "  ✗ $TICKER falhou na análise"
done

# ── 4. Status final ────────────────────────────────────────────────────────
log ""
log "FASE 4 — Status final:"
$PYTHON -m src.main status 2>&1 | tee -a "$LOG_FILE"

log ""
log "Bootstrap concluído! Log salvo em: $LOG_FILE"
