"""
Mapeamento de contas contábeis da CVM para as linhas do template.

A CVM usa códigos numéricos no padrão COSIF e IFRS.
Este arquivo mapeia esses códigos para os nomes usados no template.

Estrutura:
    MAPA_CONTAS_DRE[nome_template] = {
        "codigos_cvm": [...],   # lista de códigos que somam para essa linha
        "sinal": 1 ou -1,       # 1 = somar, -1 = inverter sinal
        "descricao": "...",
    }
"""

# ── DRE — IFRS (estrutura bancária) ──────────────────────────────────────────
# Baseado nas DFPs do Bradesco (BBDC) e Banco do Brasil (BBAS)
# Os códigos seguem o padrão da CVM: X.XX.XX.XX

MAPA_DRE_IFRS = {
    # ── Estrutura COSIF/IFRS real verificada via API CVM (Bradesco DFP 2024) ──
    # Todos os bancos listados no padrão DFP usam 3.01/3.02/3.03 para MFB
    # e 3.04.xx para itens operacionais abaixo da linha de intermediação.

    "receita_juros_total": {
        "descricao": "Receitas da Intermediação Financeira",
        # 3.01 = total receitas intermediação (soma das sub-contas)
        "codigos": ["3.01"],
        "sinal": 1,
    },
    "despesa_juros_total": {
        "descricao": "Despesas da Intermediação Financeira",
        # 3.02 = total despesas intermediação (soma das sub-contas)
        # CVM já registra como negativo — sinal=1 preserva o sinal contábil
        "codigos": ["3.02"],
        "sinal": 1,
    },
    "margem_financeira_bruta": {
        "descricao": "Resultado Bruto da Intermediação Financeira (MFB/NII)",
        # 3.03 = linha direta publicada na DRE (= 3.01 + 3.02 contabilmente)
        "codigos": ["3.03"],
        "sinal": 1,
    },
    "provisao_credito": {
        "descricao": "Provisão para Perdas Esperadas / PCLD",
        # 3.04.01 = Despesa de PCLD / Provisão para créditos duvidosos
        # CVM registra como negativo — sinal=1 preserva o sinal contábil
        "codigos": ["3.04.01"],
        "sinal": 1,
    },
    "margem_financeira_liquida": {
        "descricao": "Margem Financeira Líquida (MFB - PCLD)",
        "codigos": [],
        "sinal": 1,
        "calculado": True,   # = margem_financeira_bruta + provisao_credito
    },
    "receita_servicos": {
        "descricao": "Receitas de Prestação de Serviços e Tarifas",
        # 3.04.02 = Receitas de serviços (tarifas, administração de fundos etc.)
        "codigos": ["3.04.02"],
        "sinal": 1,
    },
    "resultado_seguros": {
        "descricao": "Resultado de Operações de Seguros, Previdência e Cap.",
        # Estrutura 2024: receita(3.04.06.01) + despesa(3.04.07.02) → net positivo
        # Estrutura 2019: resultado líquido já em 3.04.05.01
        # Cada DFP terá apenas UM desses padrões → sem dupla contagem entre anos
        "codigos": ["3.04.06.01", "3.04.07.02", "3.04.05.01"],
        "sinal": 1,
    },
    "despesa_pessoal": {
        "descricao": "Despesas de Pessoal",
        # 3.04.03 = Despesas de Pessoal
        # CVM registra como negativo — sinal=1 preserva o sinal contábil
        "codigos": ["3.04.03"],
        "sinal": 1,
    },
    "outras_despesas_operacionais": {
        "descricao": "Outras Despesas Administrativas",
        "codigos": ["3.04.04"],
        "sinal": 1,
    },
    "despesas_tributarias": {
        "descricao": "Despesas Tributárias (PIS/COFINS/ISS sobre receitas)",
        # 3.04.05 = Despesas Tributárias (verificado BBDC4 2024: -7,3 bi)
        "codigos": ["3.04.05"],
        "sinal": 1,
    },
    "depreciacao_amortizacao": {
        "descricao": "Depreciação e Amortização",
        # 3.04.07.01 = D&A (verificado BBDC4 2024: -6,0 bi)
        # IMPORTANTE: não usar 3.04.07 (pai — inclui seguros e outros itens)
        "codigos": ["3.04.07.01"],
        "sinal": 1,
    },
    "resultado_participacoes": {
        "descricao": "Resultado de Participações em Coligadas e JVs",
        # 3.04.08 = Equivalência patrimonial (Previ, coligadas)
        "codigos": ["3.04.08"],
        "sinal": 1,
    },
    "resultado_operacional": {
        "descricao": "Resultado Operacional",
        # 3.05 = subtotal operacional antes de não-recorrentes e IR
        "codigos": ["3.05"],
        "sinal": 1,
    },
    "resultado_nao_operacional": {
        "descricao": "Resultado Não Operacional / Outras receitas e despesas",
        # COSIF não segrega itens não-operacionais separadamente do 3.05
        # Deixar vazio evita dupla contagem com resultado_operacional (3.05)
        "codigos": [],
        "sinal": 1,
    },
    "resultado_antes_ir": {
        "descricao": "Resultado Antes do IR e CSLL",
        # 3.05 já é o resultado antes de IR para maioria dos bancos
        # alguns bancos usam 3.06 como "resultado antes IR"
        "codigos": ["3.05"],
        "sinal": 1,
        "calculado": True,
    },
    "ir_csll": {
        "descricao": "Imposto de Renda e Contribuição Social sobre o Lucro",
        # 3.06 = IR + CSLL (corrente + diferido)
        # CVM pode registrar positivo ou negativo dependendo do banco
        "codigos": ["3.06"],
        "sinal": 1,
    },
    "resultado_antes_minoritarios": {
        "descricao": "Resultado Antes de Participações Minoritárias",
        "codigos": ["3.07"],
        "sinal": 1,
        "calculado": True,
    },
    "participacoes_estatutarias": {
        "descricao": "Participações Estatutárias no Lucro",
        # 3.08 = PLR / participações estatutárias — CVM registra como positivo,
        # sinal=-1 porque é uma dedução para chegar ao lucro dos controladores
        "codigos": ["3.08"],
        "sinal": -1,
    },
    "participacoes_minoritarias": {
        "descricao": "Participações Minoritárias (Não Controladoras)",
        # 3.11.02 = Lucro atribuído aos não controladores — CVM registra positivo,
        # sinal=-1 porque é uma dedução para chegar ao lucro dos controladores
        "codigos": ["3.11.02"],
        "sinal": -1,
    },
    "lucro_liquido": {
        "descricao": "Lucro Líquido dos Acionistas Controladores",
        # 3.11.01 = código 2022+ (estrutura atual CVM)
        # 3.09.01 = código 2019-2021 (estrutura antiga — mesmo conteúdo)
        # Em cada DFP existe apenas UM desses padrões → sem dupla contagem
        "codigos": ["3.11.01", "3.09.01"],
        "sinal": 1,
    },
}

# ── Balanço Patrimonial — Ativo ───────────────────────────────────────────────
# Códigos no padrão IFRS CVM (DFP/ITR atual)
# Baseado na estrutura real do Bradesco, BB, Itaú (verificado via API CVM)
MAPA_ATIVO = {
    "ativo_total": {
        "descricao": "Ativo Total",
        "codigos": ["1"],
        "sinal": 1,
    },
    "disponibilidades": {
        "descricao": "Caixa e Equivalentes de Caixa",
        # 1.01 = total caixa e equiv (inclui subcategorias); usar só o total
        # evita dupla contagem com 1.01.01/1.01.02 (sub-itens do mesmo grupo)
        "codigos": ["1.01"],
        "sinal": 1,
    },
    "aplicacoes_interfinanceiras": {
        "descricao": "Aplicações Interfinanceiras de Liquidez",
        # Bradesco: 1.01.02=Aplic.Liquidez, 1.02.04.01=DepInterfinanceiros, 1.02.04.02=MercAberto
        # Itaú:    1.02.03.02=DepInterfinanceiros, 1.02.03.03=MercAberto
        "codigos": ["1.01.02", "1.02.04.01", "1.02.04.02",
                    "1.02.03.02", "1.02.03.03"],
        "sinal": 1,
    },
    "tvm_derivativos": {
        "descricao": "TVM e Instrumentos Financeiros Derivativos",
        # Bradesco: 1.02.02=ATF VJ Resultado, 1.02.03=ATF VJ ORA, 1.02.04.03=TVM CustoAmort
        # Itaú:    1.02.01.04=TVM VJ Result, 1.02.02.01=TVM VJ ORA, 1.02.03.04=TVM CustoAmort
        #          1.02.01.05=Derivativos (Itaú)
        # NOTA: NÃO incluir 1.02.03 aqui — para Itaú ele é o pai do bucket Custo Amortizado
        #       inteiro (inclui crédito). Usar sub-contas específicas.
        "codigos": ["1.02.02", "1.02.03.01", "1.02.04.03",
                    "1.02.01.04", "1.02.02.01", "1.02.03.04", "1.02.01.05"],
        "sinal": 1,
    },
    "carteira_credito_bruta": {
        "descricao": "Carteira de Crédito / Operações de Crédito (bruta)",
        # Bradesco:  1.02.04.04 = Operações de Crédito (custo amortizado)
        # Itaú:      1.02.03.05 = Operações de Crédito e Arrendamento Mercantil
        # Santander: 1.02.04.04 ou 1.02.03.05 dependendo do exercício
        "codigos": ["1.02.04.04", "1.02.03.05"],
        "sinal": 1,
    },
    "provisao_pdd": {
        "descricao": "Provisão para Perdas Esperadas (PDD/ECL)",
        # Bradesco: 1.02.04.05=PDD crédito, 1.02.04.07=PDD arrendamento
        # Itaú:    1.02.03.07=PDD (já negativo na CVM)
        "codigos": ["1.02.04.05", "1.02.04.07", "1.02.03.07"],
        "sinal": 1,
    },
    "carteira_credito_liquida": {
        "descricao": "Carteira de Crédito Líquida",
        "codigos": [],
        "calculado": True,
    },
    "ativos_remuneraveis": {
        "descricao": "Total de Ativos Remuneráveis",
        "codigos": [],
        "calculado": True,
        "componentes": ["disponibilidades", "aplicacoes_interfinanceiras",
                        "tvm_derivativos", "carteira_credito_bruta",
                        "arrendamento_mercantil", "compulsorios_bacen"],
    },
    "arrendamento_mercantil": {
        "descricao": "Operações de Arrendamento Mercantil",
        "codigos": ["1.02.04.06"],
        "sinal": 1,
    },
    "compulsorios_bacen": {
        "descricao": "Depósitos Compulsórios no Banco Central",
        # 1.02.01 = Depósito Compulsório Banco Central
        "codigos": ["1.02.01"],
        "sinal": 1,
    },
    "creditos_tributarios": {
        "descricao": "Créditos Tributários / Ativos Fiscais Diferidos",
        # 1.03.01 = IR/CSLL correntes; 1.03.02 = IR/CSLL diferidos
        "codigos": ["1.03.01", "1.03.02"],
        "sinal": 1,
    },
    "permanente": {
        "descricao": "Ativo Permanente (Investimentos + Imobilizado + Intangível)",
        # 1.05 = Investimentos; 1.06 = Imobilizado; 1.07 = Intangível
        "codigos": ["1.05", "1.06", "1.07"],
        "sinal": 1,
    },
}

# ── Balanço Patrimonial — Passivo ─────────────────────────────────────────────
# Códigos no padrão IFRS CVM (DFP/ITR atual)
# No BPP da CVM, o "Passivo Total" (código 2) inclui o Patrimônio Líquido.
# Passivos financeiros ficam em 2.01 (VJ) e 2.02 (custo amortizado).
MAPA_PASSIVO = {
    "passivo_total": {
        "descricao": "Passivo Total (inclui PL — padrão CVM)",
        # código 2 = passivo + PL na estrutura CVM IFRS
        "codigos": ["2"],
        "sinal": 1,
    },
    # Depósitos à vista / poupança / prazo não têm códigos granulares no IFRS CVM
    # O BPP IFRS só mostra depósitos total (2.02.01).
    "depositos_vista": {
        "descricao": "Depósitos à Vista (não segregado no IFRS — proxy 15% do total)",
        "codigos": [],          # sem código direto; será estimado se necessário
        "sinal": 1,
    },
    "depositos_poupanca": {
        "descricao": "Depósitos de Poupança (não segregado no IFRS — proxy 20% do total)",
        "codigos": [],
        "sinal": 1,
    },
    "depositos_prazo": {
        "descricao": "Depósitos a Prazo (não segregado no IFRS — proxy 65% do total)",
        "codigos": [],
        "sinal": 1,
    },
    "depositos_total": {
        "descricao": "Depósitos Total",
        # 2.02.01 = Depósitos (todos os tipos consolidados)
        "codigos": ["2.02.01"],
        "sinal": 1,
    },
    "captacoes_mercado_aberto": {
        "descricao": "Captações no Mercado Aberto",
        # 2.02.02 = Captações no Mercado Aberto
        "codigos": ["2.02.02"],
        "sinal": 1,
    },
    "recursos_emissao_titulos": {
        "descricao": "Recursos de Emissão de Títulos / Outras Captações",
        # 2.02.04 = Outras Captações (LCI, LCA, LF, emissões externas etc.)
        "codigos": ["2.02.04"],
        "sinal": 1,
    },
    "obrigacoes_emprestimos": {
        "descricao": "Obrigações por Empréstimos e Repasses",
        # Incluído em 2.02.04 no IFRS — sem código próprio no BPP padrão
        "codigos": [],
        "sinal": 1,
    },
    "dividas_subordinadas": {
        "descricao": "Dívidas Subordinadas / Elegíveis a Capital",
        # Incluído em 2.02.04 no IFRS — sem segregação no BPP padrão CVM
        "codigos": [],
        "sinal": 1,
    },
    "outras_obrigacoes": {
        "descricao": "Outras Obrigações (Provisões + Fiscais + Outros)",
        # 2.03 = Provisões; 2.04 = Passivos Fiscais; 2.05 = Outros Passivos
        "codigos": ["2.03", "2.04", "2.05"],
        "sinal": 1,
    },
    "passivos_financeiros_vj": {
        "descricao": "Passivos Financeiros ao Valor Justo (derivativos passivos etc.)",
        # 2.01 = Passivos Financeiros VJ através do Resultado
        "codigos": ["2.01"],
        "sinal": 1,
    },
    "passivos_onerosos_total": {
        "descricao": "Total de Passivos Onerosos",
        "codigos": [],
        "calculado": True,
        "componentes": ["depositos_total", "captacoes_mercado_aberto",
                        "recursos_emissao_titulos", "passivos_financeiros_vj"],
    },
    "patrimonio_liquido": {
        "descricao": "Patrimônio Líquido Total (consolidado)",
        # 2.07 = Patrimônio Líquido Consolidado
        "codigos": ["2.07"],
        "sinal": 1,
    },
    "pl_controladores": {
        "descricao": "PL dos Acionistas Controladores",
        # 2.07.01 = PL Atribuído ao Controlador
        "codigos": ["2.07.01"],
        "sinal": 1,
    },
}

# ── Serviços detalhados (para projeção granular) ─────────────────────────────
MAPA_SERVICOS = {
    "conta_corrente":         ["3.06.01"],
    "adm_fundos":             ["3.06.02"],
    "operacoes_credito":      ["3.06.03"],
    "cobranca":               ["3.06.04"],
    "cartao_credito_debito":  ["3.06.05"],
    "seguros_prev_cap":       ["3.06.06"],
    "arrecadacoes":           ["3.06.07"],
    "outros_servicos":        ["3.06.08", "3.06.09"],
}

# ── Indicadores da nota explicativa (quando disponíveis) ─────────────────────
MAPA_NOTAS = {
    "npl_90":                "inadimplência acima de 90 dias",
    "indice_basileia":       "índice de basileia total",
    "capital_nivel1":        "capital de nível i",
    "rwa":                   "ativos ponderados pelo risco",
    "carteira_rural":        "carteira agronegócio / rural",
    "carteira_pessoa_fisica":"carteira pessoa física",
    "carteira_pj":           "carteira pessoa jurídica",
    "cobertura_pdd":         "índice de cobertura pdd",
}

# ── Nomes alternativos por banco (alguns bancos usam terminologia diferente) ──
ALIASES_POR_BANCO = {
    "BBDC4": {
        "margem_financeira_bruta":    "Resultado de Intermediação Financeira",
        "provisao_credito":           "Despesa de Provisão para Créditos de Liquidação Duvidosa",
    },
    "BBAS3": {
        "margem_financeira_bruta":    "Resultado Bruto da Intermediação Financeira",
        "provisao_credito":           "Provisão para Créditos de Liquidação Duvidosa (PCLD Ampliada)",
    },
    "ITUB4": {
        "margem_financeira_bruta":    "Margem Financeira Gerencial",
    },
    "SANB11": {
        "margem_financeira_bruta":    "Margem de Juros Líquida",
    },
    "BPAC11": {
        "resultado_juros":            "Resultado Líquido com Instrumentos Financeiros",
    },
}
