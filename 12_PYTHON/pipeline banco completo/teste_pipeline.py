"""
teste_pipeline.py
=================
Demonstração do pipeline sem dependências externas (sem CVM, sem yfinance).
Usa dados sintéticos baseados no Bradesco 2T24 (dos modelos Excel originais).
Execute: python teste_pipeline.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from config import settings as cfg
from modules.valuation import MotorValuation
from modules.projecoes import MotorProjecoes
from modules._helpers import setup_logging

logger = setup_logging(Path("logs"), "INFO")

print("\n" + "="*65)
print("  PIPELINE DE VALUATION BANCÁRIO — TESTE COM DADOS BRADESCO")
print("="*65)

# ── Dados históricos sintéticos (baseados no modelo VAROS 2T24) ──────────────
ANOS_HIST = [2019, 2020, 2021, 2022, 2023, 2024]

dre_data = {
    "margem_financeira_bruta":       {2019:55579, 2020:63128, 2021:63980, 2022:66382, 2023:65196, 2024:62127},
    "provisao_credito":              {2019:-14408,2020:-25754,2021:-15035,2022:-32297,2023:-39545,2024:-30109},
    "margem_financeira_liquida":     {2019:41171, 2020:37374, 2021:48945, 2022:34085, 2023:25651, 2024:32018},
    "resultado_seguros":             {2019:14793, 2020:12121, 2021:11451, 2022:14761, 2023:17879, 2024:17633},
    "receita_servicos":              {2019:33606, 2020:32747, 2021:34099, 2022:35694, 2023:35642, 2024:37328},
    "despesa_pessoal":               {2019:-21767,2020:-20188,2021:-21397,2022:-23405,2023:-24908,2024:-26679},
    "outras_despesas_operacionais":  {2019:-34642,2020:-34054,2021:-33080,2022:-33728,2023:-37264,2024:-38995},
    "resultado_participacoes":       {2019:297,   2020:115,   2021:144,   2022:233,   2023:573,   2024:383},
    "resultado_operacional":         {2019:36634, 2020:28115, 2021:40162, 2022:27640, 2023:17573, 2024:21688},
    "ir_csll":                       {2019:-10568,2020:-8171, 2021:-13478,2022:-6758, 2023:-1036, 2024:-3588},
    "lucro_liquido":                 {2019:25887, 2020:19458, 2021:26215, 2022:20680, 2023:16297, 2024:17717},
}

bp_data = {
    "ativo_total":                   {2019:1695217,2020:1830247,2021:1964051,2022:2054517,2023:2054517,2024:2142747},
    "carteira_credito_bruta":        {2019:812657, 2020:891933, 2021:877285, 2022:889918, 2023:912092, 2024:951143},
    "tvm_derivativos":               {2019:725981, 2020:763292, 2021:808992, 2022:803665, 2023:821947, 2024:848200},
    "aplicacoes_interfinanceiras":   {2019:82924,  2020:121997, 2021:204614, 2022:223568, 2023:212945, 2024:215000},
    "compulsorios_bacen":            {2019:87363,  2020:101973, 2021:133722, 2022:124265, 2023:129625, 2024:132000},
    "ativos_remuneraveis":           {2019:1584791,2020:1719620,2021:1844376,2022:1873277,2023:1916028,2024:1965443},
    "provisao_pdd":                  {2019:-45236, 2020:-57741, 2021:-53901, 2022:-51643, 2023:-48508, 2024:-50585},
    "depositos_total":               {2019:560000, 2020:620000, 2021:680000, 2022:720000, 2023:760000, 2024:800000},
    "captacoes_mercado_aberto":      {2019:240000, 2020:280000, 2021:310000, 2022:330000, 2023:350000, 2024:368000},
    "recursos_emissao_titulos":      {2019:150000, 2020:180000, 2021:190000, 2022:200000, 2023:215000, 2024:225000},
    "passivos_onerosos_total":       {2019:980000, 2020:1100000,2021:1200000,2022:1270000,2023:1345000,2024:1415000},
    "patrimonio_liquido":            {2019:148900, 2020:143900, 2021:159200, 2022:158400, 2023:161200, 2024:168000},
    "pl_controladores":              {2019:145000, 2020:140000, 2021:155000, 2022:154000, 2023:157000, 2024:164000},
}

dre_hist = pd.DataFrame(dre_data).T
bp_hist  = pd.DataFrame(bp_data).T

# ── Macro histórico e projetado ──────────────────────────────────────────────
macro = {
    "historico": {
        "selic_efet":  {2019:0.0596,2020:0.0276,2021:0.0442,2022:0.1233,2023:0.1303,2024:0.1038},
        "selic_meta":  {2019:0.0450,2020:0.0200,2021:0.0925,2022:0.1375,2023:0.1175,2024:0.1065},
        "ipca":        {2019:0.0431,2020:0.0452,2021:0.1006,2022:0.0579,2023:0.0462,2024:0.0489},
        "tjlp":        {2019:0.0560,2020:0.0484,2021:0.0481,2022:0.0677,2023:0.0706,2024:0.0666},
        "cds":         {2019:0.0041,2020:0.0065,2021:0.0090,2022:0.0120,2023:0.0085,2024:0.0070},
        "inflacao_impl":{2019:0.0431,2020:0.0452,2021:0.1006,2022:0.0579,2023:0.0462,2024:0.0489},
    },
    "projecao": {
        "di":   cfg.DI_PROJETADO,
        "ipca": cfg.INFLACAO_IMPLICITA,
        "cds":  {a: cfg.CDS_PROJETADO for a in cfg.ANOS_PROJECAO},
    }
}

# ── Indicadores históricos calculados ────────────────────────────────────────
print("\n📊 INDICADORES HISTÓRICOS")
print("-"*65)
print(f"{'Ano':>6} {'ROE':>8} {'NIM':>8} {'Lucro':>10} {'Carteira':>12} {'PDD/Cart':>10}")
print("-"*65)
for ano in ANOS_HIST:
    lucro   = dre_data["lucro_liquido"][ano]
    pl      = bp_data["pl_controladores"][ano]
    mfb     = dre_data["margem_financeira_bruta"][ano]
    ar      = bp_data["ativos_remuneraveis"][ano]
    cart    = bp_data["carteira_credito_bruta"][ano]
    provisao = abs(dre_data["provisao_credito"][ano])
    roe = lucro / pl if pl else 0
    nim = mfb / ar  if ar else 0
    pdd_pct = provisao / cart if cart else 0
    print(f"{ano:>6} {roe:>8.1%} {nim:>8.2%} {lucro:>10,.0f} {cart:>12,.0f} {pdd_pct:>10.2%}")

# ── Motor de projeções ────────────────────────────────────────────────────────
print("\n🔮 PROJEÇÕES (10 ANOS)")
print("-"*65)

config_dict = {k: getattr(cfg, k) for k in dir(cfg) if not k.startswith('_')}
motor_proj  = MotorProjecoes(config_dict)

dados_norm = {"dre": dre_hist, "balanco": bp_hist, "indicadores": pd.DataFrame()}
projecoes  = motor_proj.projetar_tudo(dados_norm, macro, cfg.ANOS_PROJECAO)

print(f"\n{'Ano':>6} {'Carteira':>12} {'MFB':>10} {'Lucro':>10} {'FCFE':>10} {'NIM':>8}")
print("-"*65)
for ano in cfg.ANOS_PROJECAO[:7]:
    cart  = projecoes["carteira_credito_bruta"].get(ano, 0)
    mfb   = projecoes["margem_financeira_bruta"].get(ano, 0)
    lucro = projecoes["lucro_liquido"].get(ano, 0)
    fcfe  = projecoes["fcfe"].get(ano, 0)
    nim   = projecoes["nim"].get(ano, 0)
    print(f"{ano:>6} {cart:>12,.0f} {mfb:>10,.0f} {lucro:>10,.0f} {fcfe:>10,.0f} {nim:>8.2%}")

# ── Ke por ano ────────────────────────────────────────────────────────────────
motor_val = MotorValuation(config_dict)
ke_proj   = motor_val.calcular_ke_por_ano(
    di_proj    = cfg.DI_PROJETADO,
    cds_proj   = {a: cfg.CDS_PROJETADO for a in cfg.ANOS_PROJECAO},
    inflacao_proj = cfg.INFLACAO_IMPLICITA,
    beta       = cfg.BETA_UTILIZADO,
    erp        = cfg.PREMIO_RISCO,
)

print(f"\n📈 CUSTO DE CAPITAL (Ke) POR ANO")
print("-"*40)
for ano in cfg.ANOS_PROJECAO[:5]:
    di  = cfg.DI_PROJETADO.get(ano, 0)
    ke  = ke_proj.get(ano, 0)
    print(f"  {ano}: DI={di:.2%} → Ke={ke:.2%}")

# ── Valuation ─────────────────────────────────────────────────────────────────
COTACAO_ON = 12.55
COTACAO_PN = 14.01
ACOES_ON   = 5_294_212   # em mil
ACOES_PN   = 5_279_802   # em mil

fcfe_proj  = projecoes["fcfe"]
resultado  = motor_val.calcular_tudo(
    fcfe_proj    = fcfe_proj,
    ke_proj      = ke_proj,
    cotacao_on   = COTACAO_ON,
    cotacao_pn   = COTACAO_PN,
    acoes_on_mil = ACOES_ON,
    acoes_pn_mil = ACOES_PN,
    g            = cfg.G_PERPETUIDADE,
)

print(f"\n{'='*65}")
print(f"  VALUATION — BRADESCO (BBDC3/BBDC4)")
print(f"{'='*65}")
print(f"  VP FCFE (fase explícita):  R$ {resultado['vp_fcfe']:>10,.0f} MM")
print(f"  Valor Perpetuidade (VP):   R$ {resultado['vp_perpetuidade']:>10,.0f} MM")
print(f"  VALOR DO EQUITY:           R$ {resultado['equity_mm']:>10,.0f} MM")
print(f"  ─────────────────────────────────────────")
print(f"  Preço Justo ON (R$):         {resultado['preco_justo_on']:>8.2f}")
print(f"  Preço Justo PN (R$):         {resultado['preco_justo_pn']:>8.2f}")
print(f"  Cotação ON (R$):             {COTACAO_ON:>8.2f}")
print(f"  Cotação PN (R$):             {COTACAO_PN:>8.2f}")
print(f"  Upside ON:                   {resultado['upside_on']:>8.1%}")
print(f"  Upside PN:                   {resultado['upside_pn']:>8.1%}")
print(f"  TIR implícita (ON):          {resultado['tir_on']:>8.1%}")
print(f"  TIR implícita (PN):          {resultado['tir_pn']:>8.1%}")
print(f"  Preço Teto ON (R$):          {resultado['preco_teto_on']:>8.2f}")
print(f"  Preço Teto PN (R$):          {resultado['preco_teto_pn']:>8.2f}")
print(f"  g perpetuidade:              {resultado['g_perpetuidade']:>8.1%}")

# Checagem: % perpetuidade no valor total
pct_perp = resultado['vp_perpetuidade'] / resultado['equity_mm'] * 100
print(f"  % perpetuidade no equity:    {pct_perp:>8.1f}%")
print(f"{'='*65}")

print(f"\n✅ Pipeline executado com sucesso!")
print(f"   Execute 'python main.py --ticker BBDC4 --cotacao-on {COTACAO_ON}' para gerar o Excel.\n")
