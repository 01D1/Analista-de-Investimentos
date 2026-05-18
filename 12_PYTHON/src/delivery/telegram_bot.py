"""
telegram_bot.py
---------------
Entrega de mensagens e alertas via Telegram Bot API.

Funcionalidades:
  - Envio de texto, Markdown e arquivos
  - Formatação rica com emojis e seções
  - Retry automático em falhas de rede
  - Modo silencioso (log somente) quando token não configurado
  - Comandos de consulta (status, analyze) via webhook (opcional)

Uso:
    from src.delivery.telegram_bot import TelegramBot, get_bot

    bot = get_bot()
    bot.send("✅ BBAS3 analisado com sucesso")
    bot.send_risk_alert("PETR4", severity="high", risks=["DL/EBITDA 4.2x"])
    bot.send_morning_call_summary(path)
    bot.send_file(path_to_md)
"""

from __future__ import annotations

import time
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)

_MAX_MESSAGE_LENGTH = 4096  # limite do Telegram


class TelegramBot:
    """
    Wrapper sobre a API do Telegram para envio de notificações.

    Args:
        token:   Bot token (BotFather)
        chat_id: ID do chat/canal destino
    """

    def __init__(self, token: str | None = None, chat_id: str | None = None):
        from config.settings import settings

        self.token = token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self._enabled = bool(self.token and self.chat_id)
        if not self._enabled:
            log.debug("[Telegram] não configurado — mensagens em modo log-only")

    # ── Envio base ────────────────────────────────────────────────────────────

    def send(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_preview: bool = True,
        retry: int = 3,
    ) -> bool:
        """
        Envia mensagem de texto.

        Returns:
            True se enviado com sucesso, False se falhou ou não configurado.
        """
        if not self._enabled:
            log.info(f"[Telegram/log] {text[:120]}")
            return False

        # Truncar se necessário
        if len(text) > _MAX_MESSAGE_LENGTH:
            text = text[: _MAX_MESSAGE_LENGTH - 20] + "\n...(truncado)"

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }

        return self._post(url, payload, retry=retry)

    def send_file(
        self,
        path: Path,
        caption: str = "",
        retry: int = 3,
    ) -> bool:
        """Envia arquivo (.md, .json, .pdf) como documento."""
        if not self._enabled:
            log.info(f"[Telegram/log] arquivo: {path.name}")
            return False

        if not path.exists():
            log.warning(f"[Telegram] arquivo não encontrado: {path}")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendDocument"
        with open(path, "rb") as f:
            return self._post(
                url,
                data={"chat_id": self.chat_id, "caption": caption[:1024]},
                files={"document": (path.name, f, "text/plain")},
                retry=retry,
            )

    # ── Mensagens temáticas ───────────────────────────────────────────────────

    def send_morning_call_summary(self, path: Path) -> bool:
        """Envia resumo do morning call (primeiros 3.000 chars do arquivo)."""
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8")
        # Remover frontmatter YAML
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3 :].lstrip()
        summary = content[:3000]
        header = f"📊 *Morning Call — {path.stem.replace('morning_call_', '')}*\n\n"
        return self.send(header + summary)

    def send_risk_alert(
        self,
        ticker: str,
        severity: str,
        risks: list[str],
    ) -> bool:
        """Envia alerta de risco para um ticker."""
        icons = {"low": "ℹ️", "medium": "⚠️", "high": "🔴", "critical": "🚨"}
        icon = icons.get(severity, "⚠️")
        lines = [
            f"{icon} *Alerta de Risco — {ticker}*",
            f"Severidade: `{severity.upper()}`",
            "",
        ]
        for r in risks[:5]:
            lines.append(f"• {r}")
        return self.send("\n".join(lines))

    def send_valuation_update(
        self,
        ticker: str,
        method: str,
        fair_value: float,
        upside: float,
        current_price: float | None = None,
    ) -> bool:
        """Envia atualização de valuation."""
        direction = "📈" if upside > 0 else "📉"
        lines = [
            f"{direction} *Valuation — {ticker}*",
            f"Método: `{method}`",
            f"Fair Value: `R$ {fair_value:,.2f}`",
            f"Upside/Downside: `{upside:+.1%}`",
        ]
        if current_price:
            lines.append(f"Preço atual: `R$ {current_price:,.2f}`")
        return self.send("\n".join(lines))

    def send_job_result(
        self,
        job_name: str,
        success: bool,
        detail: str = "",
        duration_s: float | None = None,
    ) -> bool:
        """Notifica resultado de um job do scheduler."""
        icon = "✅" if success else "❌"
        dur = f" `{duration_s:.1f}s`" if duration_s is not None else ""
        text = f"{icon} *{job_name}*{dur}"
        if detail:
            text += f"\n{detail}"
        return self.send(text)

    def send_health_report(self, report: dict) -> bool:
        """Envia relatório de saúde do sistema."""
        lines = ["🏥 *Health Check*", ""]
        for item, status in report.items():
            ok = status.get("ok", False)
            msg = status.get("msg", "")
            icon = "✅" if ok else "❌"
            lines.append(f"{icon} {item}: {msg}")
        return self.send("\n".join(lines))

    def send_weekly_review(self, summary: str) -> bool:
        """Envia resumo semanal."""
        header = "📅 *Resumo Semanal — Intelligence System*\n\n"
        return self.send(header + summary[:3500])

    def send_thesis_alert(
        self,
        ticker: str,
        old_positioning: str,
        new_positioning: str,
        confidence: str,
        rationale_one_line: str,
        top_opportunity_desc: str,
    ) -> bool:
        """Envia alerta quando tese muda de posicionamento — DEL-03 / D-12."""
        text = (
            f"*{ticker}* - Tese atualizada\n"
            f"Posicionamento: {old_positioning} -> *{new_positioning}*\n"
            f"Confianca: {confidence}\n"
            f"{rationale_one_line}\n"
            f"Top oportunidade: {top_opportunity_desc}"
        )
        return self.send(text)  # self.send() ja trata truncamento em 4096 chars

    def send_daily_brief(
        self,
        macro_snapshot: dict,
        top_movers: list[dict],
        top_opportunity: dict | None,
    ) -> bool:
        """Envia resumo diario de mercado — DEL-04 / D-12."""
        from datetime import date

        date_str = date.today().strftime("%d/%m/%Y")
        selic = macro_snapshot.get("selic", 0.0)
        ptax = macro_snapshot.get("ptax", 0.0)
        ibov_pct = macro_snapshot.get("ibov_pct", 0.0)
        lines = [
            f"*Resumo de Mercado - {date_str}*",
            f"Selic: {selic:.2f}% | PTAX: R${ptax:.4f} | IBOV: {ibov_pct:+.1f}%",
            "",
            "*Top Oportunidades*",
        ]
        for i, m in enumerate(top_movers[:3], 1):
            lines.append(f"{i}. {m['ticker']}: {m['description']} (score: {m.get('score', '-')})")
        return self.send("\n".join(lines))

    # ── HTTP helper ───────────────────────────────────────────────────────────

    def _post(
        self,
        url: str,
        data: dict | None = None,
        files: dict | None = None,
        retry: int = 3,
    ) -> bool:
        import requests

        delay = 5.0
        for attempt in range(1, retry + 1):
            try:
                if files:
                    resp = requests.post(url, data=data, files=files, timeout=30)
                else:
                    resp = requests.post(url, json=data, timeout=30)

                if resp.ok:
                    return True

                body = resp.json()
                log.warning(
                    f"[Telegram] erro HTTP {resp.status_code}: "
                    f"{body.get('description', resp.text[:200])}"
                )

                # 429 = rate limit
                if resp.status_code == 429:
                    retry_after = body.get("parameters", {}).get("retry_after", delay)
                    log.info(f"[Telegram] rate limit — aguardando {retry_after}s")
                    time.sleep(float(retry_after))
                    continue

            except Exception as exc:
                log.warning(f"[Telegram] falha (tentativa {attempt}/{retry}): {exc}")

            if attempt < retry:
                time.sleep(delay)
                delay *= 2

        log.error(f"[Telegram] falha após {retry} tentativas")
        return False


# ── Singleton ─────────────────────────────────────────────────────────────────

_bot_instance: TelegramBot | None = None


def get_bot() -> TelegramBot:
    """Retorna instância singleton do TelegramBot."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBot()
    return _bot_instance
