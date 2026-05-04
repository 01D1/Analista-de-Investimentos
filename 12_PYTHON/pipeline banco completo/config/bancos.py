"""
Cadastro central de bancos — dados verificados nas fontes oficiais (RI / B3 / CVM).

Cada entrada define:
  - Tickers ON e PN/Unit na B3
  - Código CVM (usado nos downloads DFP)
  - Total de ações emitidas em MIL unidades  ← fonte: RI dos bancos (abr/2026)
  - Tipo: ON_PN | ON_ONLY | UNITS
  - Premissas específicas que sobrescrevem config/settings.py

TIPO        ESTRUTURA
--------    -----------------------------------------------
ON_PN       Duas classes: ON (BBDC3, ITUB3) + PN (BBDC4, ITUB4)
ON_ONLY     Só ON: BBAS3 (União detém ~50%; usar total emitido, não float)
UNITS       Pacote negociado: SANB11 (1ON+1PN), BPAC11 (1ON+2PN)
            → para valuation: preco_unit = equity / total_units (acoes_pn_mil = 0)

Fontes por banco (consultadas em abr/2026):
  Bradesco  → bradescori.com.br  / CVM 906
  BB        → ri.bb.com.br       / CVM 1023  (5,73 bi total; P/VP 0,72; lucro R$16,8 bi)
  Itaú      → ri.itau.com.br     / CVM 19348 (bonific. 3% dez/2025 → ~5,5 bi cada classe)
  Santander → ri.santander.com.br/ CVM 20532 (market cap R$119 bi; units R$31,67)
  BTG       → ri.btgpactual.com  / CVM 22616 (PL R$70 bi; VPA R$18; units R$64,33)
"""

BANCOS: dict[str, dict] = {

    # ── Bradesco ─────────────────────────────────────────────────────────────
    "BBDC4": {
        "nome":        "Bradesco",
        "codigo_cvm":  "906",
        "ticker_on":   "BBDC3",
        "ticker_pn":   "BBDC4",   # ticker principal (mais líquido)
        "acoes_on_mil": 5_294_000,  # ON emitidas em mil (programa recompra mai/2025: 53,4 mi ON)
        "acoes_pn_mil": 5_270_000,  # PN emitidas em mil
        "tipo":        "ON_PN",
        "relacao_pn_on": 1.10,      # PN paga dividendo 10% > ON (estatuto)
        # Premissas de projeção
        "nim_alvo":          0.050,
        "pcld_pct_alvo":     0.035,
        "payout_projetado":  0.45,
        "g_perpetuidade":    0.055,
        "beta_utilizado":    0.85,
        "crescimento_credito": {
            2025: 0.08, 2026: 0.08, 2027: 0.07, 2028: 0.07,
            2029: 0.07, 2030: 0.07, 2031: 0.06, 2032: 0.06,
            2033: 0.06, 2034: 0.06,
        },
        "crescimento_servicos": {
            2025: 0.06, 2026: 0.06, 2027: 0.065, 2028: 0.065,
            2029: 0.065, 2030: 0.065, 2031: 0.065, 2032: 0.065,
            2033: 0.065, 2034: 0.065,
        },
    },
    "BBDC3": {"alias": "BBDC4"},   # mesmo banco

    # ── Banco do Brasil ───────────────────────────────────────────────────────
    "BBAS3": {
        "nome":        "Banco do Brasil",
        "codigo_cvm":  "1023",
        "ticker_on":   "BBAS3",
        "ticker_pn":   None,
        # 5,73 bi TOTAIS emitidas (gov. federal ~50% = Treasury não reduz total emitido)
        # Yahoo retorna apenas ~2,9 bi (free float); correto é usar total emitido
        "acoes_on_mil": 5_730_000,
        "acoes_pn_mil": 0,
        "tipo":        "ON_ONLY",
        "relacao_pn_on": 1.00,
        # BB: carteira agro/gov tem spread menor; NIM ~6%, ROE ~17%, payout ~40%
        "nim_alvo":          0.060,
        "pcld_pct_alvo":     0.030,
        "payout_projetado":  0.40,
        "g_perpetuidade":    0.055,
        "beta_utilizado":    0.90,
        "crescimento_credito": {
            2025: 0.10, 2026: 0.09, 2027: 0.08, 2028: 0.08,
            2029: 0.07, 2030: 0.07, 2031: 0.06, 2032: 0.06,
            2033: 0.06, 2034: 0.06,
        },
        "crescimento_servicos": {
            2025: 0.07, 2026: 0.07, 2027: 0.065, 2028: 0.065,
            2029: 0.065, 2030: 0.065, 2031: 0.065, 2032: 0.065,
            2033: 0.065, 2034: 0.065,
        },
    },

    # ── Itaú Unibanco ─────────────────────────────────────────────────────────
    "ITUB4": {
        "nome":        "Itaú Unibanco",
        "codigo_cvm":  "19348",
        "ticker_on":   "ITUB3",
        "ticker_pn":   "ITUB4",
        # Bonificação 3% em dez/2025 → ~5,5 bi cada classe (pré-bonif: ~5,35 bi ON + ~5,33 bi PN)
        "acoes_on_mil": 5_510_000,
        "acoes_pn_mil": 5_490_000,
        "tipo":        "ON_PN",
        "relacao_pn_on": 1.10,
        # Itaú: líder em eficiência, ROE 20%+, NIM maior que Bradesco, payout ~50%
        "nim_alvo":          0.065,
        "pcld_pct_alvo":     0.032,
        "payout_projetado":  0.50,
        "g_perpetuidade":    0.055,
        "beta_utilizado":    0.80,
        "crescimento_credito": {
            2025: 0.09, 2026: 0.09, 2027: 0.08, 2028: 0.08,
            2029: 0.07, 2030: 0.07, 2031: 0.06, 2032: 0.06,
            2033: 0.06, 2034: 0.06,
        },
        "crescimento_servicos": {
            2025: 0.08, 2026: 0.08, 2027: 0.07, 2028: 0.07,
            2029: 0.07, 2030: 0.07, 2031: 0.06, 2032: 0.06,
            2033: 0.06, 2034: 0.06,
        },
    },
    "ITUB3": {"alias": "ITUB4"},

    # ── Santander Brasil ──────────────────────────────────────────────────────
    "SANB11": {
        "nome":        "Santander Brasil",
        "codigo_cvm":  "20532",
        "ticker_on":   "SANB11",   # unit mais líquida
        "ticker_pn":   None,
        # SANB11 unit = 1 ON + 1 PN; para valuation: preco_unit = equity / total_units
        # Market cap R$119 bi / R$31,67 = ~3,75 bi units
        "acoes_on_mil": 3_750_000,
        "acoes_pn_mil": 0,
        "tipo":        "UNITS",
        "relacao_pn_on": 1.00,
        # Santander: payout elevado (~80%), ROE ~10-12%, melhora gradual de eficiência
        "nim_alvo":          0.060,
        "pcld_pct_alvo":     0.040,
        "payout_projetado":  0.80,
        "g_perpetuidade":    0.050,
        "beta_utilizado":    1.00,
        "crescimento_credito": {
            2025: 0.07, 2026: 0.07, 2027: 0.06, 2028: 0.06,
            2029: 0.06, 2030: 0.06, 2031: 0.05, 2032: 0.05,
            2033: 0.05, 2034: 0.05,
        },
        "crescimento_servicos": {
            2025: 0.05, 2026: 0.05, 2027: 0.055, 2028: 0.055,
            2029: 0.055, 2030: 0.055, 2031: 0.055, 2032: 0.055,
            2033: 0.055, 2034: 0.055,
        },
    },
    "SANB3":  {"alias": "SANB11"},
    "SANB4":  {"alias": "SANB11"},

    # ── BTG Pactual ───────────────────────────────────────────────────────────
    "BPAC11": {
        "nome":        "BTG Pactual",
        "codigo_cvm":  "22616",
        "ticker_on":   "BPAC11",
        "ticker_pn":   None,
        # BPAC11 unit = 1 ON + 2 PN; para valuation: preco_unit = equity / total_units
        # PL R$70 bi; VPA R$18 (price/VP=3,57); units = 70 bi / 18 = ~3,89 bi units
        "acoes_on_mil": 3_890_000,
        "acoes_pn_mil": 0,
        "tipo":        "UNITS",
        "relacao_pn_on": 1.00,
        # BTG: banco de investimento, ROE 22%+
        # NIM blended sobre ativos remuneráveis totais (~R$557B) = MFB/AR = 9,5/557 ≈ 1,7%
        # nim_alvo = 1.7% mantém projeção internamente consistente com histórico
        # nim_maximo = 2.0% evita que regressão NIM~Selic infle o NIM artificialmente
        "nim_alvo":          0.017,
        "nim_maximo":        0.020,
        "pcld_pct_alvo":     0.010,
        "payout_projetado":  0.30,
        "g_perpetuidade":    0.060,
        "beta_utilizado":    1.10,
        "crescimento_credito": {
            2025: 0.15, 2026: 0.14, 2027: 0.12, 2028: 0.11,
            2029: 0.10, 2030: 0.09, 2031: 0.08, 2032: 0.08,
            2033: 0.07, 2034: 0.07,
        },
        "crescimento_servicos": {
            2025: 0.12, 2026: 0.12, 2027: 0.10, 2028: 0.10,
            2029: 0.09, 2030: 0.09, 2031: 0.08, 2032: 0.08,
            2033: 0.08, 2034: 0.08,
        },
        # BTG usa estrutura CVM diferente dos bancos de varejo.
        # Todos os Ativos Financeiros ficam em 1.02.xx (não 1.02.04.xx como Bradesco/BB).
        # Estes overrides substituem os codigos do MAPA_ATIVO apenas para o BTG.
        "mapa_override": {
            # 1.02.01 = Ativos Financeiros VJ (R$224B) — TVM para negociação
            # 1.02.02 = Ativos Financeiros VJ ORA (R$27B)
            # 1.02.03.05 = TVM ao custo amortizado (R$19B)
            "tvm_derivativos": {
                "codigos": ["1.02.01", "1.02.02", "1.02.03.05"],
            },
            # 1.02.03.04 = Operações de crédito (R$155B)
            "carteira_credito_bruta": {
                "codigos": ["1.02.03.04"],
            },
            # 1.02.03.01 = Aplicações mercado aberto (R$93B)
            # 1.02.03.02 = Aplicações dep. interfinanceiros (R$7B)
            "aplicacoes_interfinanceiras": {
                "codigos": ["1.02.03.01", "1.02.03.02"],
            },
            # 1.02.03.03 = Depósitos Banco Central (R$26B) — compulsórios
            # (para BTG o 1.02.01 é TVM, não compulsórios)
            "compulsorios_bacen": {
                "codigos": ["1.02.03.03"],
            },
            # Outros créditos (outros recebíveis de crédito)
            "arrendamento_mercantil": {
                "codigos": ["1.02.03.06"],
            },
        },
    },
    "BPAC3": {"alias": "BPAC11"},

    # ── Banrisul ─────────────────────────────────────────────────────────────
    "BRSR6": {
        "nome":        "Banrisul",
        "codigo_cvm":  "1120",
        "ticker_on":   "BRSR6",
        "ticker_pn":   None,
        "acoes_on_mil": 430_000,
        "acoes_pn_mil": 0,
        "tipo":        "UNITS",
        "relacao_pn_on": 1.00,
        "nim_alvo":          0.060,
        "pcld_pct_alvo":     0.040,
        "payout_projetado":  0.50,
        "g_perpetuidade":    0.050,
        "beta_utilizado":    1.00,
        "crescimento_credito": {a: 0.06 for a in range(2025, 2035)},
        "crescimento_servicos": {a: 0.05 for a in range(2025, 2035)},
    },

    # ── ABC Brasil ───────────────────────────────────────────────────────────
    "ABCB4": {
        "nome":        "ABC Brasil",
        "codigo_cvm":  "14311",
        "ticker_on":   "ABCB3",
        "ticker_pn":   "ABCB4",
        "acoes_on_mil": 72_000,
        "acoes_pn_mil": 72_000,
        "tipo":        "ON_PN",
        "relacao_pn_on": 1.10,
        "nim_alvo":          0.040,
        "pcld_pct_alvo":     0.020,
        "payout_projetado":  0.60,
        "g_perpetuidade":    0.050,
        "beta_utilizado":    0.90,
        "crescimento_credito": {a: 0.08 for a in range(2025, 2035)},
        "crescimento_servicos": {a: 0.06 for a in range(2025, 2035)},
    },
    "ABCB3": {"alias": "ABCB4"},
}


def get_banco(ticker: str) -> dict | None:
    """Retorna o dicionário do banco, resolvendo aliases."""
    t = ticker.upper()
    entry = BANCOS.get(t)
    if entry is None:
        return None
    if "alias" in entry:
        entry = BANCOS.get(entry["alias"])
    return entry


# Lista de tickers principais (sem aliases) para uso no scheduler
TICKERS_PRINCIPAIS = [
    k for k, v in BANCOS.items() if "alias" not in v
]
