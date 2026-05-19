"""
Agendador Unificado — executa e monitora news_hunter + pipeline valuation.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_VAULT      = ROOT.parents[1]
_NH_DIR     = _VAULT / "12_PYTHON" / "news_hunter"
_PL_DIR     = _VAULT / "12_PYTHON" / "pipeline banco completo"
_NH_LOG     = _NH_DIR / "news_hunter.log"
_PL_LOG_DIR = _PL_DIR / "logs"

# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
<style>
section.main > div { padding-top: 0.5rem; }

.sch-header {
    background: linear-gradient(135deg, #060B14 0%, #0D1F38 55%, #060B14 100%);
    border: 1px solid #1E3A5F; border-radius: 12px;
    padding: 18px 26px 16px; margin-bottom: 20px;
    position: relative; overflow: hidden;
}
.sch-header::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #7C3AED 0%, #3B82F6 50%, #0EA5E9 100%);
}
.sch-title { font-size: 1.4rem; font-weight: 900; color: #F1F5F9; margin: 0; }
.sch-title em { color: #3B82F6; font-style: normal; }
.sch-sub { font-size: 0.74rem; color: #334155; margin-top: 4px; }

.panel {
    background: #111827; border: 1px solid #1E2D42;
    border-radius: 10px; padding: 18px 20px; margin-bottom: 14px;
}
.panel-title {
    font-size: 0.85rem; font-weight: 800; color: #93C5FD;
    text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px;
}
.stat-grid { display: flex; gap: 16px; flex-wrap: wrap; }
.stat-item { flex: 1; min-width: 110px; }
.stat-label { font-size: 0.65rem; color: #475569; text-transform: uppercase; letter-spacing: 0.4px; }
.stat-value { font-size: 0.84rem; font-weight: 700; color: #CBD5E1; margin-top: 2px; }

.sched-pill {
    display: inline-block;
    background: #0D1F38; border: 1px solid #1E3A5F;
    padding: 2px 10px; border-radius: 12px;
    font-size: 0.7rem; font-weight: 700; color: #60A5FA; margin: 2px;
}
.txt-ok  { color: #22C55E; font-size: 0.8rem; margin: 6px 0; }
.txt-err { color: #EF4444; font-size: 0.8rem; margin: 6px 0; }

.divider {
    border: 0; border-top: 1px solid #1E2D42; margin: 20px 0;
}
</style>
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _leitura_log(caminho: Path | None, n: int = 50) -> str:
    if not caminho or not caminho.exists():
        return "(log não encontrado)"
    try:
        return "\n".join(
            caminho.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
        )
    except Exception as e:
        return f"(erro: {e})"


def _ultimo_log_pl() -> Path | None:
    if not _PL_LOG_DIR.exists():
        return None
    logs = sorted(_PL_LOG_DIR.glob("pipeline_*.log"), reverse=True)
    return logs[0] if logs else None


def _run(cmd: list[str], cwd: Path, timeout: int = 180) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            [sys.executable] + cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        out = (r.stdout + "\n" + r.stderr).strip()
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, f"Timeout ({timeout}s excedido)"
    except Exception as e:
        return False, str(e)


def _horarios_nh() -> list[str]:
    try:
        spec = importlib.util.spec_from_file_location("_nh_config", _NH_DIR / "config.py")
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "HORARIOS_ENVIO_TELEGRAM", ["07:30", "12:00", "18:00"])
    except Exception:
        return ["07:30", "12:00", "18:00"]


def _status_md(ok: bool, label: str):
    cls  = "txt-ok"  if ok else "txt-err"
    icon = "✅" if ok else "❌"
    st.markdown(f'<div class="{cls}">{icon} {label}</div>', unsafe_allow_html=True)


# ── Página ────────────────────────────────────────────────────────────────────

def main():
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="sch-header">
        <div class="sch-title">⏱ Agendador <em>Unificado</em></div>
        <div class="sch-sub">
            Executa pipelines de coleta de notícias e valuation — manual ou via agenda configurada
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_nh, col_pl = st.columns(2, gap="medium")

    # ── News Hunter ───────────────────────────────────────────────────────────
    with col_nh:
        horarios   = _horarios_nh()
        pills_html = "".join(f'<span class="sched-pill">{h}</span>' for h in horarios)

        nh_db_ok       = (_NH_DIR / "banco.db").exists()
        boletins_dir   = _NH_DIR / "boletins"
        boletins       = sorted(boletins_dir.glob("boletim_*.md"), reverse=True) if boletins_dir.exists() else []
        ult_boletim    = boletins[0].name if boletins else "—"
        ult_boletim_ts = (
            datetime.fromtimestamp(boletins[0].stat().st_mtime).strftime("%d/%m %H:%M")
            if boletins else "—"
        )

        st.markdown(f"""
        <div class="panel">
            <div class="panel-title">📡 News Hunter</div>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-label">banco.db</div>
                    <div class="stat-value">{"✅ presente" if nh_db_ok else "❌ ausente"}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Último boletim</div>
                    <div class="stat-value">{ult_boletim_ts}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Horários Telegram</div>
                    <div class="stat-value">{pills_html}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        b1, b2, b3 = st.columns(3)
        run_col  = b1.button("🔍 Coletar",  use_container_width=True, key="nh_coletar")
        run_bol  = b2.button("📋 Boletim",  use_container_width=True, key="nh_boletim")
        run_full = b3.button("🚀 Completo", use_container_width=True, key="nh_full",
                               help="Coleta + Boletim + Telegram")

        if run_col:
            with st.spinner("Coletando notícias via RSS..."):
                ok, out = _run(["main.py", "--coletar"], _NH_DIR)
            st.session_state.update(nh_ok=ok, nh_out=out,
                                    nh_lbl="Coleta concluída" if ok else "Erro na coleta")

        if run_bol:
            with st.spinner("Gerando boletim diário..."):
                ok, out = _run(["main.py", "--gerar-boletim"], _NH_DIR)
            st.session_state.update(nh_ok=ok, nh_out=out,
                                    nh_lbl="Boletim gerado" if ok else "Erro ao gerar boletim")

        if run_full:
            with st.spinner("Pipeline completo (coleta → boletim → Telegram)..."):
                ok, out = _run(["main.py", "--coletar-gerar-enviar"], _NH_DIR, timeout=240)
            st.session_state.update(nh_ok=ok, nh_out=out,
                                    nh_lbl="Pipeline completo OK" if ok else "Erro no pipeline")

        if "nh_ok" in st.session_state:
            _status_md(st.session_state["nh_ok"], st.session_state.get("nh_lbl", ""))
            with st.expander("Ver saída da execução"):
                st.code(st.session_state.get("nh_out", ""), language="")

        with st.expander("📄 Log do News Hunter (últimas 50 linhas)"):
            st.code(_leitura_log(_NH_LOG), language="")

    # ── Pipeline Valuation ────────────────────────────────────────────────────
    with col_pl:
        pl_ok       = _PL_DIR.exists()
        db_val      = _PL_DIR / "data" / "valuation.db"
        db_val_ok   = db_val.exists()
        ult_log_pl  = _ultimo_log_pl()
        ult_log_nm  = ult_log_pl.name if ult_log_pl else "—"
        ult_log_ts  = (
            datetime.fromtimestamp(ult_log_pl.stat().st_mtime).strftime("%d/%m %H:%M")
            if ult_log_pl else "—"
        )

        st.markdown(f"""
        <div class="panel">
            <div class="panel-title">📊 Pipeline Valuation</div>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-label">Pipeline</div>
                    <div class="stat-value">{"✅ encontrado" if pl_ok else "❌ não encontrado"}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">valuation.db</div>
                    <div class="stat-value">{"✅ presente" if db_val_ok else "❌ ausente"}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Último log</div>
                    <div class="stat-value">{ult_log_ts}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        ticker_in = st.text_input(
            "Ticker", value="BBAS3",
            placeholder="ex: BBAS3, WEGE3, PETR4",
            key="pl_ticker",
        )

        b4, b5, b6 = st.columns(3)
        run_single = b4.button("▶ Ticker",    use_container_width=True, key="pl_single")
        run_bancos = b5.button("🏦 Bancos",   use_container_width=True, key="pl_bancos")
        run_ind    = b6.button("🏭 Industrial", use_container_width=True, key="pl_ind")

        if run_single and ticker_in:
            with st.spinner(f"Rodando pipeline para {ticker_in.upper()}..."):
                ok, out = _run(["main.py", "--ticker", ticker_in.upper()], _PL_DIR, timeout=300)
            st.session_state.update(pl_ok=ok, pl_out=out,
                                    pl_lbl=f"Pipeline {ticker_in.upper()} OK" if ok else "Erro")

        if run_bancos:
            with st.spinner("Batch setor bancos..."):
                ok, out = _run(["main.py", "--batch-setor", "bancos"], _PL_DIR, timeout=360)
            st.session_state.update(pl_ok=ok, pl_out=out,
                                    pl_lbl="Batch bancos concluído" if ok else "Erro no batch")

        if run_ind:
            with st.spinner("Batch setor industrial..."):
                ok, out = _run(["main.py", "--batch-setor", "industrial"], _PL_DIR, timeout=360)
            st.session_state.update(pl_ok=ok, pl_out=out,
                                    pl_lbl="Batch industrial concluído" if ok else "Erro no batch")

        if "pl_ok" in st.session_state:
            _status_md(st.session_state["pl_ok"], st.session_state.get("pl_lbl", ""))
            with st.expander("Ver saída da execução"):
                st.code(st.session_state.get("pl_out", ""), language="")

        with st.expander("📄 Log do Pipeline (últimas 50 linhas)"):
            st.code(_leitura_log(ult_log_pl), language="")


main()
