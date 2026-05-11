"""
Calendário Econômico — agenda de eventos macro com CRUD via UI.
Lê/escreve diretamente em news_hunter/dados/calendario_economico.json.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_VAULT    = ROOT.parents[1]
_CAL_FILE = _VAULT / "12_PYTHON" / "news_hunter" / "dados" / "calendario_economico.json"

# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
<style>
section.main > div { padding-top: 0.5rem; }

.cal-header {
    background: linear-gradient(135deg, #060B14 0%, #0D1F38 55%, #060B14 100%);
    border: 1px solid #1E3A5F; border-radius: 12px;
    padding: 18px 26px 16px; margin-bottom: 20px;
    position: relative; overflow: hidden;
}
.cal-header::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #059669 0%, #0EA5E9 50%, #7C3AED 100%);
}
.cal-title { font-size: 1.4rem; font-weight: 900; color: #F1F5F9; margin: 0; }
.cal-title em { color: #34D399; font-style: normal; }
.cal-sub { font-size: 0.74rem; color: #334155; margin-top: 4px; }

.day-block {
    margin-bottom: 18px;
}
.day-label {
    font-size: 0.78rem; font-weight: 800; color: #60A5FA;
    text-transform: uppercase; letter-spacing: 0.8px;
    padding: 5px 0 8px 0; border-bottom: 1px solid #1E2D42;
    margin-bottom: 8px;
}
.today-badge {
    display: inline-block;
    background: #1D4ED8; color: #fff;
    padding: 1px 8px; border-radius: 8px;
    font-size: 0.62rem; font-weight: 800;
    margin-left: 8px; vertical-align: middle;
}

.ev-card {
    background: #111827; border: 1px solid #1E2D42;
    border-radius: 8px; padding: 10px 14px;
    margin-bottom: 6px;
    display: flex; align-items: center; gap: 10px;
    flex-wrap: wrap;
}
.ev-time {
    font-size: 0.82rem; font-weight: 800; color: #CBD5E1;
    font-variant-numeric: tabular-nums; min-width: 42px;
}
.ev-country {
    font-size: 0.72rem; font-weight: 700; color: #64748B;
    min-width: 44px;
}
.ev-indicator {
    font-size: 0.84rem; font-weight: 700; color: #E2E8F0;
    flex: 1;
}
.ev-imp-alta  { background:#3b0000; color:#EF4444; border:1px solid #7f1d1d; }
.ev-imp-media { background:#2d1a00; color:#F59E0B; border:1px solid #78350f; }
.ev-imp-baixa { background:#052e16; color:#22C55E; border:1px solid #166534; }
.ev-imp-badge {
    font-size: 0.62rem; font-weight: 800; letter-spacing: 0.4px;
    padding: 2px 8px; border-radius: 10px; text-transform: uppercase;
}
.ev-meta {
    font-size: 0.68rem; color: #475569;
    display: flex; gap: 12px; flex-wrap: wrap;
}
.ev-meta span { white-space: nowrap; }

.kpi-strip { display: flex; gap: 10px; margin-bottom: 18px; }
.kpi-card {
    flex: 1; background: #111827; border: 1px solid #1E2D42;
    border-radius: 10px; padding: 12px 14px; text-align: center;
}
.kpi-val { font-size: 1.4rem; font-weight: 900; color: #F1F5F9; }
.kpi-lbl { font-size: 0.66rem; color: #475569; text-transform: uppercase;
           letter-spacing: 0.4px; margin-top: 2px; }
</style>
"""

# ── Constantes ────────────────────────────────────────────────────────────────

_IMP_ICON = {"alta": "🔴", "média": "🟡", "media": "🟡", "baixa": "🟢"}
_IMP_CLS  = {
    "alta":  "ev-imp-badge ev-imp-alta",
    "média": "ev-imp-badge ev-imp-media",
    "media": "ev-imp-badge ev-imp-media",
    "baixa": "ev-imp-badge ev-imp-baixa",
}
_PAISES = ["Brasil", "EUA", "Europa", "China", "Japão", "Global", "Outro"]
_DIAS   = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# ── I/O ───────────────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if not _CAL_FILE.exists():
        return []
    try:
        data = json.loads(_CAL_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(eventos: list[dict]):
    _CAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CAL_FILE.write_text(
        json.dumps(eventos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sort(eventos: list[dict]) -> list[dict]:
    return sorted(eventos, key=lambda e: (e.get("data", ""), e.get("horario", "")))


# ── Renderização de evento ────────────────────────────────────────────────────

def _render_event(ev: dict, idx_global: int, eventos_full: list[dict]):
    imp  = ev.get("importancia", "baixa").lower()
    icon = _IMP_ICON.get(imp, "⚪")
    cls  = _IMP_CLS.get(imp, "ev-imp-badge")

    proj  = ev.get("projecao",  "—")
    ant   = ev.get("anterior",  "—")
    atual = ev.get("atual",     "—")
    if proj  in ("não disponível", "nao disponivel", ""):
        proj  = "—"
    if ant   in ("não disponível", "nao disponivel", ""):
        ant   = "—"
    if atual in ("não disponível", "nao disponivel", ""):
        atual = "—"

    col_card, col_del = st.columns([12, 1])

    with col_card:
        st.markdown(f"""
        <div class="ev-card">
            <span class="ev-time">{ev.get("horario", "--:--")}</span>
            <span class="ev-country">{ev.get("pais", "")}</span>
            <span class="ev-indicator">{ev.get("indicador", "")}</span>
            <span class="{cls}">{icon} {imp.upper()}</span>
            <div class="ev-meta">
                <span>Proj: <b>{proj}</b></span>
                <span>Ant: <b>{ant}</b></span>
                <span>Atual: <b>{atual}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_del:
        if st.button("✕", key=f"del_{idx_global}", help="Remover evento"):
            try:
                eventos_full.remove(ev)
                _save(eventos_full)
                st.rerun()
            except ValueError:
                pass


# ── Página ────────────────────────────────────────────────────────────────────

def main():
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="cal-header">
        <div class="cal-title">📅 Calendário <em>Econômico</em></div>
        <div class="cal-sub">Agenda de eventos macro · Brasil · EUA · Global</div>
    </div>
    """, unsafe_allow_html=True)

    eventos = _load()
    today   = date.today()

    # ── Filtros ───────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 3, 2])
    with fc1:
        data_de  = st.date_input("De",  value=today,                    key="cal_de")
    with fc2:
        data_ate = st.date_input("Até", value=today + timedelta(days=30), key="cal_ate")
    with fc3:
        filtro_imp = st.multiselect(
            "Importância",
            ["alta", "média", "baixa"],
            default=["alta", "média"],
            key="cal_imp",
        )
    with fc4:
        filtro_pais = st.multiselect(
            "País",
            _PAISES,
            default=[],
            placeholder="Todos",
            key="cal_pais",
        )

    de_str  = data_de.strftime("%Y-%m-%d")
    ate_str = data_ate.strftime("%Y-%m-%d")

    filtrados: list[dict] = []
    for ev in eventos:
        ev_imp  = ev.get("importancia", "baixa").lower()
        ev_pais = ev.get("pais", "")
        ev_data = ev.get("data", "")
        if ev_imp not in [i.lower() for i in filtro_imp]:
            continue
        if filtro_pais and ev_pais not in filtro_pais:
            continue
        if not (de_str <= ev_data <= ate_str):
            continue
        filtrados.append(ev)

    filtrados = _sort(filtrados)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    n_alta   = sum(1 for e in filtrados if e.get("importancia", "").lower() == "alta")
    n_media  = sum(1 for e in filtrados if e.get("importancia", "").lower() in ("média", "media"))
    n_baixa  = sum(1 for e in filtrados if e.get("importancia", "").lower() == "baixa")
    n_total  = len(filtrados)

    st.markdown(f"""
    <div class="kpi-strip">
        <div class="kpi-card">
            <div class="kpi-val" style="color:#F1F5F9">{n_total}</div>
            <div class="kpi-lbl">Total eventos</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val" style="color:#EF4444">{n_alta}</div>
            <div class="kpi-lbl">🔴 Alta importância</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val" style="color:#F59E0B">{n_media}</div>
            <div class="kpi-lbl">🟡 Média importância</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val" style="color:#22C55E">{n_baixa}</div>
            <div class="kpi-lbl">🟢 Baixa importância</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Timeline agrupada por data ────────────────────────────────────────────
    if not filtrados:
        st.info("Nenhum evento no período e filtros selecionados.")
    else:
        por_data: dict[str, list[dict]] = defaultdict(list)
        for ev in filtrados:
            por_data[ev.get("data", "")].append(ev)

        ev_counter = 0
        for dt_str in sorted(por_data):
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
                dia_sem = _DIAS[dt.weekday()]
                data_fmt = dt.strftime("%d/%m/%Y")
            except ValueError:
                dia_sem  = ""
                data_fmt = dt_str

            is_today  = dt_str == today.strftime("%Y-%m-%d")
            badge_html = '<span class="today-badge">HOJE</span>' if is_today else ""

            st.markdown(f"""
            <div class="day-block">
                <div class="day-label">{dia_sem}, {data_fmt}{badge_html}</div>
            </div>
            """, unsafe_allow_html=True)

            for ev in por_data[dt_str]:
                _render_event(ev, ev_counter, eventos)
                ev_counter += 1

    # ── Formulário: adicionar evento ──────────────────────────────────────────
    st.markdown("<hr style='border:0;border-top:1px solid #1E2D42;margin:24px 0 16px 0'>",
                unsafe_allow_html=True)

    with st.expander("➕ Adicionar evento"):
        with st.form("form_novo_evento", clear_on_submit=True):
            fa1, fa2, fa3 = st.columns(3)
            with fa1:
                nova_data      = st.date_input("Data", value=today, key="f_data")
                novo_horario   = st.text_input("Horário (HH:MM)", value="09:00", key="f_hora")
            with fa2:
                novo_pais      = st.selectbox("País", _PAISES, key="f_pais")
                nova_imp       = st.selectbox("Importância", ["alta", "média", "baixa"], key="f_imp")
            with fa3:
                novo_ind       = st.text_input("Indicador *", placeholder="ex: IPCA, FOMC, Payroll", key="f_ind")
                nova_fonte     = st.text_input("Fonte", value="manual", key="f_fonte")

            fb1, fb2, fb3 = st.columns(3)
            with fb1:
                nova_proj = st.text_input("Projeção", value="não disponível", key="f_proj")
            with fb2:
                novo_ant  = st.text_input("Anterior",  value="não disponível", key="f_ant")
            with fb3:
                novo_atu  = st.text_input("Atual",     value="não disponível", key="f_atu")

            submitted = st.form_submit_button("Adicionar evento", use_container_width=True)
            if submitted:
                if not novo_ind.strip():
                    st.error("O campo Indicador é obrigatório.")
                else:
                    novo_ev = {
                        "data":        nova_data.strftime("%Y-%m-%d"),
                        "horario":     novo_horario.strip(),
                        "pais":        novo_pais,
                        "indicador":   novo_ind.strip(),
                        "importancia": nova_imp,
                        "projecao":    nova_proj.strip(),
                        "anterior":    novo_ant.strip(),
                        "atual":       novo_atu.strip(),
                        "fonte":       nova_fonte.strip(),
                    }
                    eventos.append(novo_ev)
                    _save(eventos)
                    st.success(f"✅ '{novo_ind}' adicionado para {nova_data.strftime('%d/%m/%Y')}.")
                    st.rerun()


if __name__ == "__main__":
    main()
