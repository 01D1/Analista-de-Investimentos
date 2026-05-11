"""
Telegram Alerts — Radar Quant.

Usa o telegram_client.py do news_hunter como camada de transporte,
garantindo uma única fonte de verdade para token e chat_id.

Fallback: implementação direta via requests quando news_hunter
não está acessível (deploy em outro ambiente).

⚠️  Nunca envia ordens reais — apenas informativo.
"""
from __future__ import annotations

import logging
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("radar_quant.telegram")

# ── Localização do news_hunter ────────────────────────────────────────────────

_THIS   = Path(__file__).resolve()
_VAULT  = _THIS.parents[4]                               # raiz do vault
_NH_DIR = _VAULT / "12_PYTHON" / "news_hunter"          # pasta do news_hunter


def _nh_available() -> bool:
    return (_NH_DIR / "telegram_client.py").exists()


def _add_nh_to_path():
    nh = str(_NH_DIR)
    if nh not in sys.path:
        sys.path.insert(0, nh)


# ── Credenciais (lidas do news_hunter/config.py) ──────────────────────────────

def _load_nh_config() -> tuple[str, str, bool]:
    """Retorna (token, chat_id, ativo) lidos do config.py do news_hunter."""
    if not _nh_available():
        return "", "", False
    _add_nh_to_path()
    try:
        import importlib, types
        spec   = importlib.util.spec_from_file_location("nh_config", _NH_DIR / "config.py")
        nh_cfg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nh_cfg)
        token   = getattr(nh_cfg, "TELEGRAM_TOKEN",   "").strip()
        chat_id = getattr(nh_cfg, "TELEGRAM_CHAT_ID", "").strip()
        ativo   = bool(getattr(nh_cfg, "TELEGRAM_ATIVO", True))
        return token, chat_id, ativo
    except Exception as e:
        logger.warning("news_hunter config.py: %s", e)
        return "", "", False


# ── Envio via news_hunter telegram_client ────────────────────────────────────

def _send_via_nh(text: str) -> bool:
    """Usa enviar_mensagem() do news_hunter/telegram_client.py."""
    _add_nh_to_path()
    try:
        import importlib
        spec = importlib.util.spec_from_file_location(
            "nh_telegram", _NH_DIR / "telegram_client.py"
        )
        nh_tg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nh_tg)
        return nh_tg.enviar_mensagem(text)
    except Exception as e:
        logger.error("news_hunter telegram_client: %s", e)
        return False


# ── Fallback: requests direto ─────────────────────────────────────────────────

def _send_direct(token: str, chat_id: str, text: str) -> bool:
    try:
        import requests
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id, "text": text,
            "disable_web_page_preview": True,
        }, timeout=15)
        return resp.json().get("ok", False)
    except Exception as e:
        logger.error("Telegram direto: %s", e)
        return False


# ── API pública ───────────────────────────────────────────────────────────────

def telegram_disponivel() -> bool:
    token, chat_id, ativo = _load_nh_config()
    return bool(ativo and token and chat_id)


def send_text(text: str) -> bool:
    """Envia texto simples para o canal Telegram do news_hunter."""
    if _nh_available():
        return _send_via_nh(text)
    token, chat_id, ativo = _load_nh_config()
    if not (ativo and token and chat_id):
        logger.warning("Telegram não configurado (news_hunter ausente).")
        return False
    return _send_direct(token, chat_id, text)


def testar_conexao() -> tuple[bool, str]:
    ok = send_text(
        "🎯 Radar Quant — conexão Telegram OK!\n"
        "Alertas de setup serão enviados neste canal."
    )
    return ok, ("Conectado" if ok else "Falha — verifique config.py no news_hunter")


# ── Formatação de setup ───────────────────────────────────────────────────────

_DIR_ICON = {
    "SPREAD_ALTA": "📈", "SPREAD_BAIXA": "📉", "CONDOR": "⬌",
    "BUTTERFLY": "🦋",  "VOLATILIDADE": "⚡", "RENDA": "💰",
    "PROTECAO": "🛡",   "DIRECIONAL": "📈",
}


def _format_setup_alert(opp, rank: int = 1) -> str:
    p = opp.payoff
    main_leg  = next((l for l in p.legs if l.option_type != "STOCK"), None)
    opcao_str = main_leg.ticker if main_leg else p.name
    dir_icon  = _DIR_ICON.get(p.strategy_type, "◆")

    loss_txt   = f"R${p.max_loss:,.0f}"   if not math.isinf(p.max_loss)   else "ilimitado"
    profit_txt = f"R${p.max_profit:,.0f}" if not math.isinf(p.max_profit) else "ilimitado"
    rr_txt     = f"{p.risk_reward:.1f}x"  if not math.isinf(p.risk_reward) else "∞"
    score_bar  = "█" * int(opp.score // 10) + "░" * (10 - int(opp.score // 10))

    lines = [
        f"🎯 RADAR QUANT — Setup #{rank}",
        f"",
        f"{p.underlying}  |  {opcao_str}",
        f"{dir_icon} {p.strategy_type.replace('_',' ')}  |  DTE {p.dte}d  |  Vto {p.expiry}",
        f"",
        f"Score:    {opp.score:>5.0f}/100  {score_bar}",
        f"P(Lucro): {opp.prob_profit:>8.1%}",
        f"Risco:    {loss_txt:>10}",
        f"Alvo:     {profit_txt:>10}",
        f"R/R:      {rr_txt:>10}",
        f"",
        f"Mercado: {opp.market_condition.value}  |  Aderência {opp.scenario_adherence:.0%}",
    ]

    if main_leg:
        stop_px  = round(main_leg.price * 0.70, 4)
        alvo1_px = round(main_leg.price * 1.50, 4)
        alvo2_px = round(main_leg.price * 2.00, 4)
        lines += [
            f"",
            f"Operacao sugerida:",
            f"  Entrada: R${main_leg.price:.4f}",
            f"  Stop:    R${stop_px:.4f}  (-30%)",
            f"  Alvo 1:  R${alvo1_px:.4f}  (+50%)",
            f"  Alvo 2:  R${alvo2_px:.4f}  (+100%)",
        ]

    lines += [
        f"",
        f"AVISO: apenas informativo — decisao e execucao sao do operador.",
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
    ]
    return "\n".join(lines)


def _format_daily_summary(opps: list) -> str:
    total    = len(opps)
    n_op     = sum(1 for o in opps if o.status == "OPERACIONAL")
    avg_sc   = sum(o.score for o in opps) / total if total else 0
    avg_pp   = sum(o.prob_profit for o in opps) / total if total else 0
    n_ativos = len({o.payoff.underlying for o in opps})

    top_line = ""
    if opps:
        top = max(opps, key=lambda o: o.score)
        top_line = f"\nMelhor setup: {top.payoff.underlying} | Score {top.score:.0f}"

    return (
        f"RESUMO DIARIO — Radar Quant\n"
        f"{datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"Estruturas:  {total}\n"
        f"Ativos:      {n_ativos}\n"
        f"Operacional: {n_op}\n"
        f"Score medio: {avg_sc:.0f}\n"
        f"P(lucro) av: {avg_pp:.0%}"
        f"{top_line}\n\n"
        f"AVISO: apenas informativo."
    )


# ── Deduplicação diária ───────────────────────────────────────────────────────

_SENT_TODAY: set[str] = set()


def _key(opp) -> str:
    return f"{date.today()}|{opp.payoff.underlying}|{opp.name}"


def _already_sent(opp) -> bool:
    return _key(opp) in _SENT_TODAY


def _mark_sent(opp):
    _SENT_TODAY.add(_key(opp))


# ── Filtro ────────────────────────────────────────────────────────────────────

def _should_send(
    opp,
    min_score: float = 70.0,
    min_prob: float = 0.55,
    only_op: bool = True,
    only_definido: bool = True,
    deduplicate: bool = True,
) -> tuple[bool, str]:
    if only_op and opp.status != "OPERACIONAL":
        return False, "não operacional"
    if opp.score < min_score:
        return False, f"score {opp.score:.0f} < {min_score:.0f}"
    if opp.prob_profit < min_prob:
        return False, f"P(lucro) {opp.prob_profit:.0%} < {min_prob:.0%}"
    if only_definido and opp.payoff.risk_level != "DEFINIDO":
        return False, "risco ilimitado"
    if deduplicate and _already_sent(opp):
        return False, "já enviado hoje"
    return True, "ok"


# ── Disparo em lote ───────────────────────────────────────────────────────────

def send_top_setups(
    opps: list,
    min_score: float = 70.0,
    min_prob: float = 0.55,
    max_alerts: int = 5,
) -> list[dict]:
    """
    Filtra e envia os melhores setups.
    Retorna: [{"opp": opp, "sent": bool, "reason": str}]
    """
    results = []
    rank = 0

    for opp in sorted(opps, key=lambda o: o.score, reverse=True):
        ok, reason = _should_send(opp, min_score, min_prob)
        if not ok:
            results.append({"opp": opp, "sent": False, "reason": reason})
            continue

        rank += 1
        if rank > max_alerts:
            results.append({"opp": opp, "sent": False, "reason": "limite atingido"})
            continue

        msg = _format_setup_alert(opp, rank)
        ok_send = send_text(msg)
        if ok_send:
            _mark_sent(opp)
        results.append({"opp": opp, "sent": ok_send,
                        "reason": "enviado" if ok_send else "falha no envio"})

    return results


def send_daily_summary(opps: list) -> bool:
    """Envia resumo diário do scanner."""
    return send_text(_format_daily_summary(opps))
