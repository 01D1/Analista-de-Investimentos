"""
Configurações globais do pipeline de valuation.
Suporta bancos e empresas não-financeiras de qualquer setor.

Premissas específicas por empresa/setor: ver config/empresas.yaml
Este arquivo contém apenas defaults globais e parâmetros de infraestrutura.
"""
from pathlib import Path

# Carregar credenciais do .env compartilhado em 12_PYTHON/.env (D-03)
# pipeline banco completo/config/ → parent = config/ → parent.parent = pipeline banco completo/
# → parent.parent.parent = 12_PYTHON/
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

# ── Diretórios ─────────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent.parent
CACHE_DIR   = ROOT_DIR / "cache"
OUTPUT_DIR  = ROOT_DIR / "outputs"
LOG_DIR     = ROOT_DIR / "logs"
TEMPLATE    = ROOT_DIR.parent / "Template_Valuation_Banco.xlsx"

# ── Empresa alvo (pode ser sobrescrito via CLI ou empresas.yaml) ──────────────
TICKER_B3       = "BBDC4"          # Default; qualquer ticker cadastrado no YAML funciona
NOME_EMPRESA    = "Bradesco"
CNPJ            = "60.746.948/0001-12"  # CNPJ para busca na CVM

# Código CVM (fallback — empresas.yaml é a fonte de verdade)
# Consulte: https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/
CODIGO_CVM      = "906"

# ── Períodos (calculados dinamicamente) ───────────────────────────────────────
# Último DFP disponível: se estamos após abril, o DFP do ano anterior já saiu.
# Ex: em abril/2026 → DFP 2025 disponível → histórico até 2025, projeção 2026-2035.
from datetime import datetime as _dt
_hoje = _dt.now()
# CVM publica DFP até ~março do ano seguinte; em abril/2026 o DFP 2025 já está disponível.
_ultimo_dfp = _hoje.year - 1
_n_hist     = 6   # quantos anos de histórico
_n_proj     = 10  # quantos anos de projeção

ANOS_HISTORICOS = list(range(_ultimo_dfp - _n_hist + 1, _ultimo_dfp + 1))
ANOS_PROJECAO   = list(range(_ultimo_dfp + 1, _ultimo_dfp + 1 + _n_proj))
# Trimestre mais recente: Q1 do ano atual se estivermos após jan, senão Q4 do ano anterior
_mes_atual = _hoje.month
if _mes_atual >= 5:       # mai+ → 1T do ano atual publicado (prazo CVM = 45 dias do fim do trimestre)
    TRIMESTRE_ATUAL = f"1T{str(_hoje.year)[-2:]}"
elif _mes_atual >= 1:     # jan–abr → último dado é 4T (DFP) do ano anterior
    TRIMESTRE_ATUAL = f"4T{str(_ultimo_dfp)[-2:]}"

# ── Premissas de Ke (editáveis) ────────────────────────────────────────────────
# Projeções do DI (fonte: Focus/BCB) — gerado dinamicamente por ano de projeção
# Convergência: começa mais alto e converge para ~9% no longo prazo
_di_curva = [0.1300, 0.1100, 0.1050, 0.1000, 0.0970, 0.0940, 0.0920, 0.0910, 0.0900, 0.0900]
DI_PROJETADO = {a: _di_curva[min(i, len(_di_curva)-1)] for i, a in enumerate(ANOS_PROJECAO)}
BETA_UTILIZADO      = 0.85     # Beta arbitrado (conservador)
PREMIO_RISCO        = 0.065    # ERP Brasil — fonte: FGV/Damodaran
CDS_PROJETADO       = 0.004    # CDS médio projetado
_infl_curva = [0.050, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045]
INFLACAO_IMPLICITA  = {a: _infl_curva[min(i, len(_infl_curva)-1)] for i, a in enumerate(ANOS_PROJECAO)}

# ── Premissas de crescimento (projeção) ───────────────────────────────────────
_cresc_cred = [0.08, 0.08, 0.07, 0.07, 0.07, 0.07, 0.06, 0.06, 0.06, 0.06]
CRESCIMENTO_CARTEIRA_CREDITO = {a: _cresc_cred[min(i, len(_cresc_cred)-1)] for i, a in enumerate(ANOS_PROJECAO)}
_cresc_serv = [0.06, 0.06, 0.065, 0.065, 0.065, 0.065, 0.065, 0.065, 0.065, 0.065]
CRESCIMENTO_SERVICOS = {a: _cresc_serv[min(i, len(_cresc_serv)-1)] for i, a in enumerate(ANOS_PROJECAO)}
# Spread com clientes (NIM): converge para mediana histórica
NIM_ALVO    = 0.050    # NIM total de balanço (MFB/ativos remuneráveis) — mediana histórica Bradesco
NIM_ATUAL   = None     # será preenchido pelo normalizador

# Provisão: % da carteira — converge para média histórica
PCLD_PCT_ALVO   = 0.035
PCLD_PCT_ATUAL  = None

# CAPEX como % dos ativos (baixo para bancos)
CAPEX_PCT_ATIVO = 0.0015

# Crescimento na perpetuidade
G_PERPETUIDADE  = 0.055    # PIB nominal longo prazo (nominal: IPCA ~4.5% + real ~1%)

# Basileia mínimo alvo (para cálculo de capital regulatório)
BASILEIA_ALVO   = 0.135

# ── Payout e dividendos ───────────────────────────────────────────────────────
PAYOUT_PROJETADO = 0.45     # % do lucro distribuído

# ── Relação PN/ON ─────────────────────────────────────────────────────────────
RELACAO_PN_ON   = 1.10

# ── Premissas WACC — empresas não-financeiras (defaults globais) ──────────────
# Valores por empresa/setor: ver empresas.yaml → premissas
CUSTO_DIVIDA_SPREAD = 0.02        # Spread sobre CDI para custo da dívida
ALIQUOTA_IR_NOMINAL = 0.34        # IR+CSLL nominal (34%)
MARGEM_EBITDA_ALVO  = 0.25        # Margem EBITDA convergência (override por setor)
CAPEX_PCT_RECEITA   = 0.05        # CAPEX % receita (override por setor)
NCG_PCT_RECEITA     = 0.15        # NCG % receita (override por setor)
_cresc_rec = [0.08, 0.07, 0.07, 0.06, 0.06, 0.06, 0.055, 0.055, 0.055, 0.055]
CRESCIMENTO_RECEITA_DEFAULT = {a: _cresc_rec[min(i, len(_cresc_rec)-1)] for i, a in enumerate(ANOS_PROJECAO)}

# ── Formatação Excel ──────────────────────────────────────────────────────────
UNIDADE_VALORES = "MM"   # MM = milhões, MN = bilhões
DIVISOR_VALORES = 1_000       # CVM reporta em R$ milhares (divisor para MM)

# ── Cache ─────────────────────────────────────────────────────────────────────
USAR_CACHE      = True     # False força re-download sempre
CACHE_TTL_HORAS = 24       # Revalidar cache após 24h

# ── APIs ─────────────────────────────────────────────────────────────────────
CVM_BASE_URL    = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
BCB_BASE_URL    = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
IBGE_BASE_URL   = "https://servicodados.ibge.gov.br/api/v3"

# Códigos de séries do BCB
BCB_SERIES = {
    "selic_meta":     432,    # Taxa Selic meta (% a.a.)
    "selic_diaria":   11,     # Selic Over diária
    "di":             12,     # DI (CETIP)
    "ipca_mensal":    433,    # IPCA mensal
    "ipca_12m":       13522,  # IPCA acumulado 12m
    "tjlp":           256,    # TJLP
    "cambio_dolar":   1,      # USD/BRL
    "pib_nominal":    4380,   # PIB nominal
    "pib_variacao":   4385,   # PIB variação
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"   # DEBUG, INFO, WARNING, ERROR
