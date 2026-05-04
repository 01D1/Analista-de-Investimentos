"""
llm_client.py
-------------
Cliente centralizado para Anthropic Claude API com:
  - Prompt caching (system prompts como `cache_control: ephemeral`)
  - Rate limiting com backoff exponencial
  - Retry automático em 429/529/overload
  - Leitura de prompts do vault Obsidian (11_PROMPTS/)
  - Dois modelos configuráveis: content (Sonnet) e classify (Haiku)

Uso:
    from src.content.llm_client import LLMClient

    client = LLMClient()
    response = client.generate(
        system_prompt="Você é um analista...",
        user_message="Analise BBAS3...",
        use_cache=True,
    )
    print(response)
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

from src.utils.logger import get_logger

log = get_logger(__name__)

# Prompts lidos do vault
_PROMPT_ANALISTA = "11_PROMPTS/PROMPT_ANALISTA.md"
_PROMPT_REDATOR = "11_PROMPTS/PROMPT_REDATOR_RESEARCH.md"
_PROMPT_CONSTRUTOR = "11_PROMPTS/PROMPT_CONSTRUTOR_TESE.md"


class LLMClient:
    """
    Wrapper sobre o SDK Anthropic com prompt caching e retry.

    Args:
        model_content:  Modelo para geração de conteúdo (Sonnet)
        model_classify: Modelo para classificação rápida (Haiku)
        max_retries:    Tentativas após rate limit / overload
        retry_delay:    Delay base em segundos (exponential backoff)
    """

    def __init__(
        self,
        model_content: str | None = None,
        model_classify: str | None = None,
        max_retries: int = 4,
        retry_delay: float = 10.0,
    ):
        from config.settings import settings

        self._settings = settings
        self.model_content = model_content or settings.claude_model_content
        self.model_classify = model_classify or settings.claude_model_classify
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Any = None  # lazy

    @property
    def client(self):
        """Anthropic client — inicializado sob demanda."""
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(
                api_key=self._settings.anthropic_api_key,
            )
        return self._client

    # ── Geração principal ─────────────────────────────────────────────────────

    def generate(
        self,
        user_message: str,
        system_prompt: str | None = None,
        use_cache: bool = True,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """
        Gera texto com Claude.

        Args:
            user_message:  Mensagem do usuário com o contexto/dados
            system_prompt: Prompt do sistema (será cacheado se use_cache=True)
            use_cache:     Adiciona cache_control ao system prompt para reduzir custo
            model:         Modelo a usar (default: model_content)
            max_tokens:    Máximo de tokens na resposta
            temperature:   Temperatura da geração

        Returns:
            Texto gerado pelo modelo
        """
        model = model or self.model_content

        messages = [{"role": "user", "content": user_message}]

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            if use_cache:
                kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                kwargs["system"] = system_prompt

        return self._call_with_retry(**kwargs)

    def classify(
        self,
        user_message: str,
        system_prompt: str | None = None,
        max_tokens: int = 256,
    ) -> str:
        """Chamada rápida com Haiku para classificação."""
        return self.generate(
            user_message=user_message,
            system_prompt=system_prompt,
            model=self.model_classify,
            max_tokens=max_tokens,
            temperature=0.0,
            use_cache=False,
        )

    # ── Retry com backoff ─────────────────────────────────────────────────────

    def _call_with_retry(self, **kwargs) -> str:
        import anthropic

        delay = self.retry_delay
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.messages.create(**kwargs)
                # Logar uso de cache se disponível
                usage = getattr(response, "usage", None)
                if usage:
                    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
                    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
                    if cache_read or cache_write:
                        log.debug(
                            f"[LLM] cache_read={cache_read} cache_write={cache_write} "
                            f"input={usage.input_tokens} output={usage.output_tokens}"
                        )
                return response.content[0].text

            except anthropic.RateLimitError as exc:
                log.warning(f"[LLM] rate limit (tentativa {attempt}/{self.max_retries}): {exc}")
            except anthropic.InternalServerError as exc:
                log.warning(f"[LLM] server error (tentativa {attempt}/{self.max_retries}): {exc}")
            except anthropic.APIStatusError as exc:
                if exc.status_code in (529,):
                    log.warning(f"[LLM] overload 529 (tentativa {attempt}/{self.max_retries})")
                else:
                    raise

            if attempt < self.max_retries:
                log.info(f"[LLM] aguardando {delay:.0f}s antes de retry...")
                time.sleep(delay)
                delay = min(delay * 2, 120.0)  # cap em 2 min

        raise RuntimeError(f"[LLM] falha após {self.max_retries} tentativas")

    # ── Leitura de prompts do vault ───────────────────────────────────────────

    def read_vault_prompt(self, relative_path: str) -> str:
        """Lê um arquivo de prompt do vault Obsidian."""
        p = self._settings.vault_path / relative_path
        if not p.exists():
            log.warning(f"[LLM] prompt não encontrado: {p}")
            return ""
        return p.read_text(encoding="utf-8")

    @lru_cache(maxsize=8)
    def prompt_analista(self) -> str:
        return self.read_vault_prompt(_PROMPT_ANALISTA)

    @lru_cache(maxsize=8)
    def prompt_redator(self) -> str:
        return self.read_vault_prompt(_PROMPT_REDATOR)

    @lru_cache(maxsize=8)
    def prompt_construtor_tese(self) -> str:
        return self.read_vault_prompt(_PROMPT_CONSTRUTOR)


# ── Singleton ─────────────────────────────────────────────────────────────────

_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Retorna instância singleton do LLMClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance
