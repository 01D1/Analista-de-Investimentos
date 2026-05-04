"""
Mapeamento de contas contábeis CVM → linhas do template VAROS
para empresas NÃO-FINANCEIRAS (IFRS padrão).

Estrutura CVM IFRS padrão (verificada com WEG DFP 2024):
  DRE:  3.01 Receita → 3.02 CPV → 3.03 Lucro Bruto → 3.05 EBIT → 3.11.01 LL
  BPA:  1.01 Circulante → 1.02 Não Circulante
  BPP:  2.01 Passivo Circ → 2.02 Não Circ → 2.03 PL
  DFC:  6.01 Operacional → 6.02 Investimento → 6.03 Financiamento

Diferenças-chave vs. bancos (COSIF):
  - Bancos: 3.01=Receita Intermediação, 3.03=MFB, DRE estrutura COSIF
  - Geral:  3.01=Receita Líquida, 3.03=Lucro Bruto, DRE estrutura CPC/IFRS
  - Bancos: Ativo → carteira crédito, depósitos, compulsórios
  - Geral:  Ativo → estoque, clientes, imobilizado, intangível
  - Bancos: Ke (FCFE). Geral: WACC (FCFF)
"""

# ═══════════════════════════════════════════════════════════════════════════════
# DRE — IFRS Padrão (empresas não-financeiras)
# Códigos verificados: WEG (5410), Suzano (18538), Rumo (21725)
# ═══════════════════════════════════════════════════════════════════════════════

MAPA_DRE_GERAL = {

    # ── Receita e Custo ──────────────────────────────────────────────────────
    "receita_liquida": {
        "descricao": "Receita de Venda de Bens e/ou Serviços",
        "codigos": ["3.01"],
        "sinal": 1,
    },
    "custo_mercadorias": {
        "descricao": "Custo dos Bens e/ou Serviços Vendidos (CPV/CMV)",
        # CVM registra como negativo
        "codigos": ["3.02"],
        "sinal": 1,
    },
    "lucro_bruto": {
        "descricao": "Resultado Bruto (Receita - CPV)",
        "codigos": ["3.03"],
        "sinal": 1,
    },

    # ── Despesas Operacionais ────────────────────────────────────────────────
    "despesas_operacionais_total": {
        "descricao": "Despesas/Receitas Operacionais (total)",
        "codigos": ["3.04"],
        "sinal": 1,
    },
    "despesas_vendas": {
        "descricao": "Despesas com Vendas",
        # CVM registra como negativo
        "codigos": ["3.04.01"],
        "sinal": 1,
    },
    "despesas_gerais_adm": {
        "descricao": "Despesas Gerais e Administrativas",
        "codigos": ["3.04.02"],
        "sinal": 1,
    },
    "perdas_impairment": {
        "descricao": "Perdas pela Não Recuperabilidade de Ativos (Impairment)",
        "codigos": ["3.04.03"],
        "sinal": 1,
    },
    "outras_receitas_operacionais": {
        "descricao": "Outras Receitas Operacionais",
        "codigos": ["3.04.04"],
        "sinal": 1,
    },
    "outras_despesas_operacionais": {
        "descricao": "Outras Despesas Operacionais",
        "codigos": ["3.04.05"],
        "sinal": 1,
    },
    "resultado_equivalencia": {
        "descricao": "Resultado de Equivalência Patrimonial",
        "codigos": ["3.04.06"],
        "sinal": 1,
    },

    # ── EBIT ─────────────────────────────────────────────────────────────────
    "ebit": {
        "descricao": "Resultado Antes do Resultado Financeiro e dos Tributos (EBIT)",
        "codigos": ["3.05"],
        "sinal": 1,
    },

    # ── Resultado Financeiro ─────────────────────────────────────────────────
    "resultado_financeiro": {
        "descricao": "Resultado Financeiro Líquido",
        "codigos": ["3.06"],
        "sinal": 1,
    },
    "receitas_financeiras": {
        "descricao": "Receitas Financeiras",
        "codigos": ["3.06.01"],
        "sinal": 1,
    },
    "despesas_financeiras": {
        "descricao": "Despesas Financeiras",
        # CVM registra como negativo
        "codigos": ["3.06.02"],
        "sinal": 1,
    },

    # ── Resultado pré-IR ─────────────────────────────────────────────────────
    "resultado_antes_ir": {
        "descricao": "Resultado Antes dos Tributos sobre o Lucro (EBT)",
        "codigos": ["3.07"],
        "sinal": 1,
    },
    "ir_csll": {
        "descricao": "Imposto de Renda e Contribuição Social sobre o Lucro",
        "codigos": ["3.08"],
        "sinal": 1,
    },
    "ir_corrente": {
        "descricao": "IR/CSLL Corrente",
        "codigos": ["3.08.01"],
        "sinal": 1,
    },
    "ir_diferido": {
        "descricao": "IR/CSLL Diferido",
        "codigos": ["3.08.02"],
        "sinal": 1,
    },

    # ── Lucro Líquido ────────────────────────────────────────────────────────
    "resultado_operacoes_continuadas": {
        "descricao": "Resultado Líquido das Operações Continuadas",
        "codigos": ["3.09"],
        "sinal": 1,
    },
    "resultado_operacoes_descontinuadas": {
        "descricao": "Resultado Líquido de Operações Descontinuadas",
        "codigos": ["3.10"],
        "sinal": 1,
    },
    "lucro_liquido_consolidado": {
        "descricao": "Lucro/Prejuízo Consolidado do Período",
        "codigos": ["3.11"],
        "sinal": 1,
    },
    "lucro_liquido": {
        "descricao": "Lucro Líquido Atribuído aos Controladores",
        "codigos": ["3.11.01"],
        "sinal": 1,
    },
    "participacoes_minoritarias": {
        "descricao": "Lucro Atribuído a Não Controladores",
        "codigos": ["3.11.02"],
        "sinal": 1,
    },

    # ── Calculados (não vêm direto da CVM) ───────────────────────────────────
    "ebitda": {
        "descricao": "EBITDA (EBIT + D&A)",
        "codigos": [],
        "sinal": 1,
        "calculado": True,
        # = ebit + depreciacao_amortizacao (extraída da DFC)
    },
    "margem_bruta": {
        "descricao": "Margem Bruta (%)",
        "codigos": [],
        "sinal": 1,
        "calculado": True,
        "tipo": "percentual",
    },
    "margem_ebitda": {
        "descricao": "Margem EBITDA (%)",
        "codigos": [],
        "sinal": 1,
        "calculado": True,
        "tipo": "percentual",
    },
    "margem_liquida": {
        "descricao": "Margem Líquida (%)",
        "codigos": [],
        "sinal": 1,
        "calculado": True,
        "tipo": "percentual",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# BALANÇO PATRIMONIAL — Ativo (IFRS padrão)
# ═══════════════════════════════════════════════════════════════════════════════

MAPA_ATIVO_GERAL = {
    "ativo_total": {
        "descricao": "Ativo Total",
        "codigos": ["1"],
        "sinal": 1,
    },

    # ── Ativo Circulante ─────────────────────────────────────────────────────
    "ativo_circulante": {
        "descricao": "Ativo Circulante",
        "codigos": ["1.01"],
        "sinal": 1,
    },
    "caixa_equivalentes": {
        "descricao": "Caixa e Equivalentes de Caixa",
        "codigos": ["1.01.01"],
        "sinal": 1,
    },
    "aplicacoes_financeiras_cp": {
        "descricao": "Aplicações Financeiras de Curto Prazo",
        "codigos": ["1.01.02"],
        "sinal": 1,
    },
    "contas_receber": {
        "descricao": "Contas a Receber (Clientes)",
        "codigos": ["1.01.03"],
        "sinal": 1,
    },
    "estoques": {
        "descricao": "Estoques",
        "codigos": ["1.01.04"],
        "sinal": 1,
    },
    "ativos_biologicos_cp": {
        "descricao": "Ativos Biológicos (curto prazo)",
        "codigos": ["1.01.05"],
        "sinal": 1,
    },
    "tributos_recuperar_cp": {
        "descricao": "Tributos a Recuperar (curto prazo)",
        "codigos": ["1.01.06"],
        "sinal": 1,
    },
    "despesas_antecipadas": {
        "descricao": "Despesas Antecipadas",
        "codigos": ["1.01.07"],
        "sinal": 1,
    },
    "outros_ativos_circulantes": {
        "descricao": "Outros Ativos Circulantes",
        "codigos": ["1.01.08"],
        "sinal": 1,
    },

    # ── Ativo Não Circulante ─────────────────────────────────────────────────
    "ativo_nao_circulante": {
        "descricao": "Ativo Não Circulante",
        "codigos": ["1.02"],
        "sinal": 1,
    },
    "realizavel_longo_prazo": {
        "descricao": "Ativo Realizável a Longo Prazo",
        "codigos": ["1.02.01"],
        "sinal": 1,
    },
    "investimentos": {
        "descricao": "Investimentos",
        "codigos": ["1.02.02"],
        "sinal": 1,
    },
    "imobilizado": {
        "descricao": "Imobilizado",
        "codigos": ["1.02.03"],
        "sinal": 1,
    },
    "intangivel": {
        "descricao": "Intangível",
        "codigos": ["1.02.04"],
        "sinal": 1,
    },

    # ── Calculados ────────────────────────────────────────────────────────────
    "capital_de_giro": {
        "descricao": "Necessidade de Capital de Giro (NCG)",
        "codigos": [],
        "calculado": True,
        # = contas_receber + estoques - fornecedores
    },
    "divida_bruta": {
        "descricao": "Dívida Bruta (empréstimos CP + LP)",
        "codigos": [],
        "calculado": True,
        # = emprestimos_cp + emprestimos_lp
    },
    "divida_liquida": {
        "descricao": "Dívida Líquida (Dívida Bruta - Caixa - Aplicações)",
        "codigos": [],
        "calculado": True,
        # = divida_bruta - caixa_equivalentes - aplicacoes_financeiras_cp
    },
    "capital_investido": {
        "descricao": "Capital Investido (PL + Dívida Líquida)",
        "codigos": [],
        "calculado": True,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# BALANÇO PATRIMONIAL — Passivo (IFRS padrão)
# ═══════════════════════════════════════════════════════════════════════════════

MAPA_PASSIVO_GERAL = {
    "passivo_total": {
        "descricao": "Passivo Total (inclui PL)",
        "codigos": ["2"],
        "sinal": 1,
    },

    # ── Passivo Circulante ───────────────────────────────────────────────────
    "passivo_circulante": {
        "descricao": "Passivo Circulante",
        "codigos": ["2.01"],
        "sinal": 1,
    },
    "obrigacoes_sociais": {
        "descricao": "Obrigações Sociais e Trabalhistas",
        "codigos": ["2.01.01"],
        "sinal": 1,
    },
    "fornecedores": {
        "descricao": "Fornecedores",
        "codigos": ["2.01.02"],
        "sinal": 1,
    },
    "obrigacoes_fiscais_cp": {
        "descricao": "Obrigações Fiscais (curto prazo)",
        "codigos": ["2.01.03"],
        "sinal": 1,
    },
    "emprestimos_cp": {
        "descricao": "Empréstimos e Financiamentos (curto prazo)",
        "codigos": ["2.01.04"],
        "sinal": 1,
    },
    "outras_obrigacoes_cp": {
        "descricao": "Outras Obrigações (curto prazo)",
        "codigos": ["2.01.05"],
        "sinal": 1,
    },
    "provisoes_cp": {
        "descricao": "Provisões (curto prazo)",
        "codigos": ["2.01.06"],
        "sinal": 1,
    },

    # ── Passivo Não Circulante ───────────────────────────────────────────────
    "passivo_nao_circulante": {
        "descricao": "Passivo Não Circulante",
        "codigos": ["2.02"],
        "sinal": 1,
    },
    "emprestimos_lp": {
        "descricao": "Empréstimos e Financiamentos (longo prazo)",
        "codigos": ["2.02.01"],
        "sinal": 1,
    },
    "outras_obrigacoes_lp": {
        "descricao": "Outras Obrigações (longo prazo)",
        "codigos": ["2.02.02"],
        "sinal": 1,
    },
    "tributos_diferidos": {
        "descricao": "Tributos Diferidos",
        "codigos": ["2.02.03"],
        "sinal": 1,
    },
    "provisoes_lp": {
        "descricao": "Provisões (longo prazo)",
        "codigos": ["2.02.04"],
        "sinal": 1,
    },

    # ── Patrimônio Líquido ───────────────────────────────────────────────────
    "patrimonio_liquido": {
        "descricao": "Patrimônio Líquido Consolidado",
        "codigos": ["2.03"],
        "sinal": 1,
    },
    "capital_social": {
        "descricao": "Capital Social Realizado",
        "codigos": ["2.03.01"],
        "sinal": 1,
    },
    "reservas_capital": {
        "descricao": "Reservas de Capital",
        "codigos": ["2.03.02"],
        "sinal": 1,
    },
    "reservas_lucros": {
        "descricao": "Reservas de Lucros",
        "codigos": ["2.03.04"],
        "sinal": 1,
    },
    "pl_controladores": {
        "descricao": "PL Atribuído aos Controladores",
        "codigos": [],
        "calculado": True,
        # = patrimonio_liquido - participacoes_minoritarias_pl
    },
    "participacoes_minoritarias_pl": {
        "descricao": "Participação dos Acionistas Não Controladores (PL)",
        "codigos": ["2.03.09"],
        "sinal": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# DFC — Fluxo de Caixa (Método Indireto)
# ═══════════════════════════════════════════════════════════════════════════════

MAPA_DFC_GERAL = {
    "fluxo_operacional": {
        "descricao": "Caixa Líquido de Atividades Operacionais",
        "codigos": ["6.01"],
        "sinal": 1,
    },
    "caixa_gerado_operacoes": {
        "descricao": "Caixa Gerado nas Operações (antes de variação de CG)",
        "codigos": ["6.01.01"],
        "sinal": 1,
    },
    "variacao_ativos_passivos": {
        "descricao": "Variações nos Ativos e Passivos (Capital de Giro)",
        "codigos": ["6.01.02"],
        "sinal": 1,
    },
    "fluxo_investimento": {
        "descricao": "Caixa Líquido de Atividades de Investimento",
        "codigos": ["6.02"],
        "sinal": 1,
    },
    "capex_imobilizado": {
        "descricao": "Aquisição de Imobilizado (CAPEX)",
        # CVM registra como negativo
        "codigos": ["6.02.02"],
        "sinal": 1,
    },
    "capex_intangivel": {
        "descricao": "Aquisição de Intangível",
        "codigos": ["6.02.03"],
        "sinal": 1,
    },
    "fluxo_financiamento": {
        "descricao": "Caixa Líquido de Atividades de Financiamento",
        "codigos": ["6.03"],
        "sinal": 1,
    },
    "captacao_emprestimos": {
        "descricao": "Captação de Empréstimos e Financiamentos",
        "codigos": ["6.03.01"],
        "sinal": 1,
    },
    "pagamento_emprestimos": {
        "descricao": "Pagamento de Empréstimos e Financiamentos",
        "codigos": ["6.03.02"],
        "sinal": 1,
    },
    "dividendos_pagos": {
        "descricao": "Pagamento de Dividendos e JCP",
        "codigos": ["6.03.04"],
        "sinal": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Função seletora: retorna o mapeamento correto dado o tipo de empresa
# ═══════════════════════════════════════════════════════════════════════════════

def get_mapeamento(tipo_empresa: str) -> dict:
    """
    Retorna os mapas de contas corretos baseado no tipo de empresa.

    Args:
        tipo_empresa: "bank" ou "general"

    Returns:
        dict com chaves "dre", "ativo", "passivo", "dfc"
    """
    if tipo_empresa == "bank":
        # Importa o mapeamento bancário existente
        from config.mapeamento_contas import (
            MAPA_DRE_IFRS, MAPA_ATIVO, MAPA_PASSIVO
        )
        return {
            "dre": MAPA_DRE_IFRS,
            "ativo": MAPA_ATIVO,
            "passivo": MAPA_PASSIVO,
            "dfc": {},  # bancos não usam DFC no pipeline atual
        }
    else:
        return {
            "dre": MAPA_DRE_GERAL,
            "ativo": MAPA_ATIVO_GERAL,
            "passivo": MAPA_PASSIVO_GERAL,
            "dfc": MAPA_DFC_GERAL,
        }
