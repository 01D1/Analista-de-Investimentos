"""
src/valuation/sector_normalizer.py — Sector Normalization Layer (M016-S01)

Converte valores GICS/type do banco e do tickers.yaml em chaves canônicas
aceitas pelo router (BANK, COMMODITY, UTILITY, RETAIL, INDUSTRY, HOLDING,
TECH, INSURANCE) ou retorna FALLBACK_MULTIPLES quando não há mapeamento.

Problema resolvido:
  - Banco e tickers.yaml: financials, energy, materials, utilities, ...
  - Router espera: BANK, COMMODITY, UTILITY, RETAIL, INDUSTRY, HOLDING, TECH
  - Sem normalização: todos os 28 tickers elegíveis caem em FALLBACK (confidence=0.5)

Fontes de resolução (por precedência):
  1. canonical_pass-through  — setor já é chave canônica (ex: "BANK")
  2. explicit_type            — campo type passado diretamente (ex: type="bank")
  3. tickers_yaml_type        — type lookup no tickers.yaml via ticker
  4. gics_sector_fallback     — mapeamento sector GICS (ex: "financials" → BANK)
  5. subsector_hint           — subsector como dica adicional (raro)
  6. fallback_multiples       — não mapeável → confidence=0.5, nunca raise

Decisões registradas:
  D099 — type (yaml) é fonte primária; sector GICS é fallback
  D100 — type desconhecido → FALLBACK_MULTIPLES (nunca raise, nunca inventar)
  D108 — healthcare + agro + education → INDUSTRY canonical key
  D108 — real_estate → HOLDING canonical key

Proibido:
  - Calcular fair_value
  - Alterar banco
  - Criar mocks
  - Lançar exceção por setor desconhecido
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Chaves canônicas do router ─────────────────────────────────────────────────

#: Conjunto completo de chaves canônicas aceitas pelo router
CANONICAL_KEYS: frozenset[str] = frozenset({
    "BANK",
    "INSURANCE",
    "COMMODITY",
    "UTILITY",
    "INDUSTRY",
    "RETAIL",
    "HOLDING",
    "TECH",
})

#: Chave usada quando não há mapeamento possível
FALLBACK_CANONICAL: str = "FALLBACK_MULTIPLES"


# ── Tabela de mapeamento: type (tickers.yaml) → chave canônica ─────────────────

#: Mapeamento autoritativo via campo `type` do tickers.yaml (D099)
TYPE_TO_CANONICAL: dict[str, str] = {
    # Financeiro — Bancos
    "bank":          "BANK",
    # Financeiro — Seguros
    "insurance":     "INSURANCE",
    "reinsurance":   "INSURANCE",
    # Energia — Petróleo & Gás, Mineração
    "oil_gas":       "COMMODITY",
    "mining":        "COMMODITY",
    # Utilities
    "utilities":     "UTILITY",
    # Industrial (inclui transporte, celulose, alimentos, automóvel) (D108)
    "industrial":    "INDUSTRY",
    "healthcare":    "INDUSTRY",   # sem modelo próprio em M016 (D108)
    "agro":          "INDUSTRY",   # sem modelo próprio em M016 (D108)
    "education":     "INDUSTRY",   # sem modelo próprio em M016 (D108)
    # Varejo
    "retail":        "RETAIL",
    # Holdings e Real Estate (D108)
    "holding":       "HOLDING",
    "real_estate":   "HOLDING",
    # Tecnologia / Telecom
    "technology":    "TECH",
    "telecom":       "TECH",
}

#: Aliases extras: abreviações e variantes conhecidas de type
_TYPE_ALIASES: dict[str, str] = {
    "oil":           "oil_gas",
    "gas":           "oil_gas",
    "oil_and_gas":   "oil_gas",
    "oilgas":        "oil_gas",
    "pulp_paper":    "industrial",
    "paper":         "industrial",
    "food":          "industrial",
    "beverages":     "industrial",
    "transport":     "industrial",
    "logistics":     "industrial",
    "auto":          "industrial",
    "auto_parts":    "industrial",
    "construction":  "industrial",
    "steel":         "industrial",
    "chemical":      "industrial",
    "pharma":        "healthcare",
    "pharmacy":      "healthcare",
    "diagnostics":   "healthcare",
    "insurer":       "insurance",
    "realty":        "real_estate",
    "fii":           "real_estate",
    "tech":          "technology",
    "software":      "technology",
    "infra":         "utilities",
    "infrastructure":"utilities",
    "power":         "utilities",
    "water":         "utilities",
    "sanitation":    "utilities",
}


# ── Tabela de mapeamento: sector GICS (banco/yaml) → chave canônica ────────────

#: Mapeamento fallback via setor GICS (D099)
#: Usado quando não há `type` disponível. Menos preciso que type.
GICS_SECTOR_TO_CANONICAL: dict[str, str] = {
    # Financeiro: bank é o mais comum; holdings também caem aqui sem type
    "financials":               "BANK",
    # Energia
    "energy":                   "COMMODITY",
    # Materiais: mineração, siderurgia, celulose
    "materials":                "COMMODITY",
    # Utilities
    "utilities":                "UTILITY",
    # Varejo / Consumo
    "consumer_discretionary":   "RETAIL",
    "consumer_staples":         "RETAIL",
    # Saúde (D108)
    "healthcare":               "INDUSTRY",
    # Comunicação / Telecom
    "communication":            "TECH",
    "communication_services":   "TECH",
    # Tecnologia
    "technology":               "TECH",
    "information_technology":   "TECH",
    # Industrial
    "industrials":              "INDUSTRY",
    "industrial":               "INDUSTRY",
    # Imóveis
    "real_estate":              "HOLDING",
}


# ── Fontes de resolução ────────────────────────────────────────────────────────

class NormalizationSource:
    CANONICAL_PASSTHROUGH = "canonical_passthrough"  # já era canônico
    EXPLICIT_TYPE         = "explicit_type"          # type= passado diretamente
    TICKERS_YAML_TYPE     = "tickers_yaml_type"      # type= do tickers.yaml (via ticker lookup)
    GICS_SECTOR_FALLBACK  = "gics_sector_fallback"   # sector GICS como fallback
    SUBSECTOR_HINT        = "subsector_hint"         # subsector como dica
    FALLBACK_MULTIPLES    = "fallback_multiples"     # não mapeável


# ── Resultado da normalização ──────────────────────────────────────────────────

@dataclass
class SectorNormalizationResult:
    """Resultado da normalização setorial de um ticker.

    Campos
    ------
    ticker: str
        Código do ativo B3 (uppercase).
    raw_sector: str | None
        Setor GICS original do banco/yaml (ex: "financials", "energy").
    raw_type: str | None
        Campo type do tickers.yaml (ex: "bank", "oil_gas").
    raw_subsector: str | None
        Subsector original, se disponível.
    canonical_sector: str
        Chave canônica do router (ex: "BANK", "COMMODITY").
        Sempre preenchido — nunca None. Fallback: "FALLBACK_MULTIPLES".
    confidence: float
        Confiança da normalização:
        1.0 — type canônico rastreável (yaml ou explícito)
        0.8 — GICS sector fallback (menos preciso)
        0.5 — FALLBACK_MULTIPLES (não mapeável)
    source: str
        Qual fonte determinou o canonical_sector (NormalizationSource constants).
    fallback_used: bool
        True se canonical_sector == FALLBACK_MULTIPLES.
    notes: str
        Explicação do resultado para auditoria e debugging.
    """

    ticker: str
    raw_sector: Optional[str] = None
    raw_type: Optional[str] = None
    raw_subsector: Optional[str] = None
    canonical_sector: str = FALLBACK_CANONICAL
    confidence: float = 0.5
    source: str = NormalizationSource.FALLBACK_MULTIPLES
    fallback_used: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        self.ticker = str(self.ticker).strip().upper()
        self.fallback_used = (self.canonical_sector == FALLBACK_CANONICAL)


# ── Funções internas ───────────────────────────────────────────────────────────

def _resolve_type_alias(raw: str) -> str:
    """Normaliza type: lowercase + strip + alias lookup."""
    cleaned = raw.strip().lower()
    return _TYPE_ALIASES.get(cleaned, cleaned)


def _type_to_canonical(raw_type: str) -> Optional[str]:
    """Converte type para chave canônica. Retorna None se não mapeável."""
    normalized = _resolve_type_alias(raw_type)
    return TYPE_TO_CANONICAL.get(normalized)


def _gics_to_canonical(raw_sector: str) -> Optional[str]:
    """Converte sector GICS para chave canônica. Retorna None se não mapeável."""
    cleaned = raw_sector.strip().lower().replace("-", "_").replace(" ", "_")
    return GICS_SECTOR_TO_CANONICAL.get(cleaned)


# ── Interface pública ──────────────────────────────────────────────────────────

def normalize_sector(
    ticker: str,
    sector: Optional[str] = None,
    type: Optional[str] = None,  # noqa: A002 — shadowing built-in OK aqui (nome do campo yaml)
    subsector: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> SectorNormalizationResult:
    """Normaliza sector + type → chave canônica do router.

    Parâmetros
    ----------
    ticker: str
        Código do ativo B3 (ex: "BBAS3", "PETR4"). Case-insensitive.
    sector: str | None
        Setor GICS do banco/yaml (ex: "financials", "energy", "materials").
    type: str | None
        Campo type do tickers.yaml (ex: "bank", "oil_gas", "industrial").
        Tem precedência sobre sector.
    subsector: str | None
        Subsector adicional (raro, usado como hint).
    metadata: dict | None
        Metadados adicionais (reservado para extensão futura).

    Retorno
    -------
    SectorNormalizationResult
        Resultado canônico. canonical_sector sempre preenchido.
        Nunca lança exceção.

    Exemplos
    --------
    >>> normalize_sector("BBAS3", sector="financials", type="bank")
    SectorNormalizationResult(ticker="BBAS3", canonical_sector="BANK", confidence=1.0)

    >>> normalize_sector("PETR4", sector="energy")
    SectorNormalizationResult(ticker="PETR4", canonical_sector="COMMODITY", confidence=0.8)

    >>> normalize_sector("UNKNOWN", sector="xyz")
    SectorNormalizationResult(ticker="UNKNOWN", canonical_sector="FALLBACK_MULTIPLES", confidence=0.5)
    """
    ticker_up = str(ticker).strip().upper()
    raw_sector = str(sector).strip() if sector else None
    raw_type   = str(type).strip() if type else None
    raw_sub    = str(subsector).strip() if subsector else None

    # ── Passo 0: passthrough se sector já é chave canônica ──────────────────────
    if raw_sector and raw_sector.upper() in CANONICAL_KEYS:
        return SectorNormalizationResult(
            ticker=ticker_up,
            raw_sector=raw_sector,
            raw_type=raw_type,
            raw_subsector=raw_sub,
            canonical_sector=raw_sector.upper(),
            confidence=1.0,
            source=NormalizationSource.CANONICAL_PASSTHROUGH,
            fallback_used=False,
            notes=f"Setor '{raw_sector}' já é chave canônica — passthrough.",
        )
    if raw_type and raw_type.upper() in CANONICAL_KEYS:
        return SectorNormalizationResult(
            ticker=ticker_up,
            raw_sector=raw_sector,
            raw_type=raw_type,
            raw_subsector=raw_sub,
            canonical_sector=raw_type.upper(),
            confidence=1.0,
            source=NormalizationSource.CANONICAL_PASSTHROUGH,
            fallback_used=False,
            notes=f"Type '{raw_type}' já é chave canônica — passthrough.",
        )

    # ── Passo 1: type explícito passado como parâmetro ──────────────────────────
    if raw_type:
        canonical = _type_to_canonical(raw_type)
        if canonical:
            return SectorNormalizationResult(
                ticker=ticker_up,
                raw_sector=raw_sector,
                raw_type=raw_type,
                raw_subsector=raw_sub,
                canonical_sector=canonical,
                confidence=1.0,
                source=NormalizationSource.EXPLICIT_TYPE,
                fallback_used=False,
                notes=f"type='{raw_type}' → canonical='{canonical}' (mapeamento explícito).",
            )
        # type presente mas não mapeado — continua tentando sector
        logger.debug("ticker=%s: type='%s' não mapeado, tentando sector GICS", ticker_up, raw_type)

    # ── Passo 2: lookup do ticker no tickers.yaml ────────────────────────────────
    from src.valuation.tickers_config import get_ticker_config  # lazy import

    ticker_cfg = get_ticker_config(ticker_up)
    if ticker_cfg:
        yaml_type = ticker_cfg.get("type")
        if yaml_type:
            canonical = _type_to_canonical(yaml_type)
            if canonical:
                return SectorNormalizationResult(
                    ticker=ticker_up,
                    raw_sector=raw_sector or ticker_cfg.get("sector"),
                    raw_type=yaml_type,
                    raw_subsector=raw_sub,
                    canonical_sector=canonical,
                    confidence=1.0,
                    source=NormalizationSource.TICKERS_YAML_TYPE,
                    fallback_used=False,
                    notes=(
                        f"tickers.yaml: type='{yaml_type}' → canonical='{canonical}' "
                        f"(ticker={ticker_up})."
                    ),
                )
        # ticker no yaml mas sem type mapeado — usar sector do yaml como fallback
        if not raw_sector:
            raw_sector = ticker_cfg.get("sector")

    # ── Passo 3: sector GICS como fallback ──────────────────────────────────────
    effective_sector = raw_sector or (ticker_cfg.get("sector") if ticker_cfg else None)
    if effective_sector:
        canonical = _gics_to_canonical(effective_sector)
        if canonical:
            return SectorNormalizationResult(
                ticker=ticker_up,
                raw_sector=effective_sector,
                raw_type=raw_type,
                raw_subsector=raw_sub,
                canonical_sector=canonical,
                confidence=0.8,
                source=NormalizationSource.GICS_SECTOR_FALLBACK,
                fallback_used=False,
                notes=(
                    f"sector='{effective_sector}' (GICS fallback) → canonical='{canonical}'. "
                    "Considere definir type no tickers.yaml para confidence=1.0."
                ),
            )

    # ── Passo 4: subsector como hint adicional ──────────────────────────────────
    if raw_sub:
        canonical = _gics_to_canonical(raw_sub)
        if canonical:
            return SectorNormalizationResult(
                ticker=ticker_up,
                raw_sector=raw_sector,
                raw_type=raw_type,
                raw_subsector=raw_sub,
                canonical_sector=canonical,
                confidence=0.7,
                source=NormalizationSource.SUBSECTOR_HINT,
                fallback_used=False,
                notes=f"subsector='{raw_sub}' como hint → canonical='{canonical}'.",
            )

    # ── Passo 5: FALLBACK_MULTIPLES — nunca raise ────────────────────────────────
    raw_info = " | ".join(filter(None, [
        f"sector={raw_sector!r}" if raw_sector else None,
        f"type={raw_type!r}" if raw_type else None,
    ])) or "nenhum dado de setor"

    return SectorNormalizationResult(
        ticker=ticker_up,
        raw_sector=raw_sector,
        raw_type=raw_type,
        raw_subsector=raw_sub,
        canonical_sector=FALLBACK_CANONICAL,
        confidence=0.5,
        source=NormalizationSource.FALLBACK_MULTIPLES,
        fallback_used=True,
        notes=(
            f"Não foi possível mapear para chave canônica ({raw_info}). "
            "Usando FALLBACK_MULTIPLES. Verifique type no tickers.yaml."
        ),
    )


# ── Classe de conveniência ─────────────────────────────────────────────────────

class SectorNormalizer:
    """Wrapper stateless para normalize_sector com suporte a batch.

    Uso básico
    ----------
    >>> normalizer = SectorNormalizer()
    >>> result = normalizer.normalize("BBAS3")
    >>> result.canonical_sector
    'BANK'

    >>> batch = normalizer.normalize_batch(["BBAS3", "PETR4", "EGIE3"])
    >>> {r.ticker: r.canonical_sector for r in batch}
    {'BBAS3': 'BANK', 'PETR4': 'COMMODITY', 'EGIE3': 'UTILITY'}
    """

    def normalize(
        self,
        ticker: str,
        sector: Optional[str] = None,
        type: Optional[str] = None,  # noqa: A002
        subsector: Optional[str] = None,
    ) -> SectorNormalizationResult:
        """Normaliza um único ticker.

        Se sector/type não passados, faz lookup no tickers.yaml automaticamente.
        """
        return normalize_sector(ticker=ticker, sector=sector, type=type, subsector=subsector)

    def normalize_batch(
        self,
        tickers: list[str],
        sector_map: Optional[dict[str, str]] = None,
        type_map: Optional[dict[str, str]] = None,
    ) -> list[SectorNormalizationResult]:
        """Normaliza múltiplos tickers.

        Parâmetros
        ----------
        tickers: list[str]
            Lista de tickers B3.
        sector_map: dict[str, str] | None
            Mapeamento opcional ticker → sector (para override por ticker).
        type_map: dict[str, str] | None
            Mapeamento opcional ticker → type (para override por ticker).

        Retorno
        -------
        list[SectorNormalizationResult]
            Um resultado por ticker, na mesma ordem.
        """
        results = []
        sm = sector_map or {}
        tm = type_map or {}
        for t in tickers:
            t_up = str(t).strip().upper()
            results.append(
                normalize_sector(
                    ticker=t_up,
                    sector=sm.get(t_up),
                    type=tm.get(t_up),
                )
            )
        return results

    def get_canonical(self, ticker: str) -> str:
        """Retorna apenas o canonical_sector. Conveniente para router inline."""
        return self.normalize(ticker).canonical_sector

    def is_routable(self, ticker: str) -> bool:
        """True se canonical_sector ≠ FALLBACK_MULTIPLES."""
        return self.get_canonical(ticker) != FALLBACK_CANONICAL

    def smoke_test(self, tickers: list[str]) -> dict:
        """Roda normalização nos tickers e retorna sumário para auditoria.

        Retorno
        -------
        dict com:
          - results: list[SectorNormalizationResult]
          - routable: list[str]
          - fallback: list[str]
          - by_canonical: dict[str, list[str]]
          - confidence_avg: float
        """
        results = self.normalize_batch(tickers)
        routable = [r.ticker for r in results if not r.fallback_used]
        fallback_tickers = [r.ticker for r in results if r.fallback_used]

        by_canonical: dict[str, list[str]] = {}
        for r in results:
            by_canonical.setdefault(r.canonical_sector, []).append(r.ticker)

        avg_conf = sum(r.confidence for r in results) / len(results) if results else 0.0

        return {
            "results": results,
            "routable": routable,
            "fallback": fallback_tickers,
            "by_canonical": by_canonical,
            "confidence_avg": round(avg_conf, 3),
            "total": len(results),
            "routable_count": len(routable),
            "fallback_count": len(fallback_tickers),
        }


# ── Singleton conveniente ──────────────────────────────────────────────────────

_default_normalizer: Optional[SectorNormalizer] = None


def get_normalizer() -> SectorNormalizer:
    """Retorna instância singleton do SectorNormalizer."""
    global _default_normalizer
    if _default_normalizer is None:
        _default_normalizer = SectorNormalizer()
    return _default_normalizer


# ── Exports ────────────────────────────────────────────────────────────────────

__all__ = [
    # Constantes
    "CANONICAL_KEYS",
    "FALLBACK_CANONICAL",
    "TYPE_TO_CANONICAL",
    "GICS_SECTOR_TO_CANONICAL",
    # Enumeração de fontes
    "NormalizationSource",
    # Dataclass de resultado
    "SectorNormalizationResult",
    # Função principal
    "normalize_sector",
    # Classe de conveniência
    "SectorNormalizer",
    # Singleton
    "get_normalizer",
]
