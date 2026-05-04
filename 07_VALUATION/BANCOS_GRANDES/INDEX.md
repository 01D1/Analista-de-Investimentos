---
title: Valuation — Bancos Grandes (Round 1 + BPAC11)
tags:
  - valuation
  - bancos
  - ddm
data-base: 2025-12-31
status: 5-bancos-completos
---

# Valuation — Bancos Grandes Brasileiros

> Modelos de valuation 2026-2030 + Terminal para os 4 bancos tradicionais de grande porte **+ BTG Pactual (banco de investimento)**. Metodologia DDM (Gordon 2 estágios) com checagem por múltiplos históricos.

---

## Resumo Executivo (cenário base — abr/2026)

| Ticker | Preço | Alvo DDM | Upside | Recomendação | Ke | ROE '26E | ROE '30E | LL '26E (R$ bi) | LL '30E (R$ bi) |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| [[VALUATION_ITUB4_2026\|ITUB4]]  | 35,50 | 30,45 | -14,2% | NEUTRO-   | 17,7% | 26,9% | 24,8% | 58,5 | 86,8 |
| [[VALUATION_BBAS3_2026\|BBAS3]]  | 26,80 | 20,62 | -23,0% | VENDA     | 18,3% | 12,9% | 16,6% | 25,3 | 45,7 |
| [[VALUATION_BBDC4_2026\|BBDC4]]  | 15,20 |  7,93 | -47,8% | VENDA     | 18,6% | 12,8% | 15,8% | 23,8 | 43,5 |
| [[VALUATION_SANB11_2026\|SANB11]] | 29,80 | 22,62 | -24,1% | VENDA     | 18,0% | 14,8% | 15,7% | 19,3 | 27,8 |
| [[VALUATION_BPAC11_2026\|BPAC11]] | 42,50 | 24,83 | -41,6% | VENDA     | 18,3% | 17,1% | 21,6% | 13,1 | 26,1 |

> 📊 **Comparativa side-by-side dos 5**: [[COMPARATIVA_BANCOS_5]] — dashboard com ranking, scorecard de 5 métricas (upside, ROE, Ke, P/L, spread ROE-Ke) e gráficos.

> [!warning] Limitações do cenário base
> - **Dados históricos têm lacunas**: PDD, OPEX e algumas linhas do BP foram **estimadas** quando ausentes no pipeline CVM. Ver nota em cada aba `3.Historico`.
> - **Preços atuais são referência** (não snapshot intradiário). Substitua na célula `C7` da Capa para atualizar upside.
> - **Cenário base é conservador**: custo de crédito declina gradualmente, eficiência melhora, carteira cresce 6-9% a.a.
> - **BPAC11**: modelo DDM tradicional subestima bancos fee-heavy com baixo payout — premium do mercado (P/L 8x) não é justificável por DDM puro mas captura growth premium. Ver `Learning Log 2026-04-17`.

---

## Ranking Agregado (5 métricas)

Scorecard em `COMPARATIVA_BANCOS_5.xlsx` aba `6.Ranking` — menor score = melhor posicionado:

| # | Ticker | Score | Rec. | Leitura |
|---|---|:---:|---|---|
| 1º | **ITUB4** | ~8 | NEUTRO- | Melhor qualidade operacional (ROE 27%), menor desconto ao alvo |
| 2º | **BPAC11** | ~13 | VENDA | ROE alto mas premium de mercado agressivo |
| 3º | **SANB11** | ~14 | VENDA | ROE médio, P/L razoável, mas descomprimindo |
| 4º | **BBAS3** | ~16 | VENDA | Risco regulatório + ROE inferior aos pares privados |
| 5º | **BBDC4** | ~19 | VENDA | Deterioração operacional estrutural 2020-2024 |

---

## Estrutura padrão de cada .xlsx

Todos os 5 arquivos seguem a mesma arquitetura — **11 abas, 606 fórmulas, zero erros**:

| # | Aba | Conteúdo |
|---|---|---|
| 1 | **Capa** | Sumário executivo, navegação, premissas-chave, legenda de cores |
| 2 | **Premissas** | Macro (Rf, ERP, β → Ke via CAPM), payout, ROE sustentável, drivers ano-a-ano (carteira, NIM, custo crédito, OPEX, eficiência) |
| 3 | **Histórico** | DRE + BP 2019-2025 + indicadores calculados (ROE, ROA, NIM, eficiência, custo crédito, alavancagem) |
| 4 | **Drivers** | Bridge histórico × projeção — carteira, NIM, custo crédito, OPEX, ROE, eficiência |
| 5 | **DRE Proj** | Projeção 2026-2030 + Terminal (NII = Ativos Médios × NIM; OPEX = Receita × Eficiência; IR 35%; payout projetado). **Métricas efetivas calculadas** (ROE do ano, NIM efetivo, Eficiência, Margem Líq., Custo Crédito) para cross-check de consistência |
| 6 | **BP Proj** | Balanço completo projetado: **Ativo decomposto** (Carteira, Interfinanceiras+TVM, Outros, PDD memo), **Passivo decomposto** (Depósitos, Captações/Dívida Sub., Outros, Total Passivo), **PL com reconciliação** (PL inicial + LL − Div = PL final, Δ check), **Indicadores regulatórios** (RWA proxy, Basileia proxy, Check Ativo=Passivo+PL), Alavancagem |
| 7 | **DDM** | Gordon 2 estágios: dividendos 2026-2030 descontados a Ke + TV perpetuidade; decomposição Estágio 1 vs Terminal |
| 8 | **Múltiplos** | P/L, P/VP, DY históricos (2019-2025) + implícitos no preço-alvo + **forward** (LPA/VPA projetados 2026, P/L fwd, P/VP fwd, DY proj, EV/Ativos, ROE implícito no preço atual via Gordon reverso) |
| 9 | **Sensibilidade** | Tabela 2D: Ke (12-17%) × g (3,5-6%) com heatmap |
| 10 | **Dashboard** | KPIs + 3 gráficos (LL, ROE×NIM, Carteira) histórico + projeção |
| 11 | **Cenários** | **Stress / Base / Blue-Sky** — 8 variáveis (Rf, ERP, β, Ke calculado, g, crescimento carteira, custo crédito, ROE sustentável) × 3 cenários; preço-alvo Gordon 1-stage por cenário (`VPA × (ROE-g)/(Ke-g)`), upside e recomendação implícita, heatmap |

---

## Metodologia — Premissas macro compartilhadas

| Parâmetro | Valor | Fonte |
|---|---:|---|
| Rf (NTN-B 2035 proxy) | 11,5% | Tesouro Direto |
| ERP Brasil (já inclui CRP) | 6,5% | Damodaran 2025 |
| Inflação média 2026-30 | 3,5% | BCB Focus |
| g terminal (nominal) | 5,0% | Inflação + real 1,5% |
| Alíquota IR/CSLL | 35,0% | Bancos no Brasil |

### Betas específicos por banco
| Ticker | β | Racional |
|---|:---:|---|
| ITUB4 | 0,95 | Defensivo, blue-chip do setor |
| BBAS3 | 1,05 | Exposição ao risco regulatório/fiscal |
| BBDC4 | 1,10 | Deterioração operacional eleva volatilidade |
| SANB11 | 1,00 | Neutro, subsidiária de multinacional |
| BPAC11 | 1,05 | IB volátil, mas beta maduro pós-IPO (2024-25) |

> [!note] CAPM sem double-counting de risco-país
> O ERP_Brasil da Damodaran **já embute** o Country Risk Premium (spread soberano). Somar CRP novamente à fórmula `Rf + β·ERP + CRP` duplica o risco. Este modelo usa: **Ke = Rf + β·ERP_BR**. Risco-país fica no workbook apenas como referência informativa.

---

## Aprendizados-chave (do Learning Log)

1. **DDM subestima bancos fee-heavy com baixo payout** — Gordon 2 estágios assume valor flui via dividendos. BPAC11 com payout 30% deixa valor em retained earnings que o modelo não captura bem. Ajuste: usar payout efetivo incluindo JCP + recompras (45% para BPAC).
2. **Template "NIM × Ativos"** não captura receita de IB/AM/S&T — para BPAC foi necessário elevar NIM projetado para 5-5,4% (proxy de "return on assets" total) e calibrar tarifas históricas pela reconciliação com LL real.
3. **Ke alto (18-19%) no Brasil comprime valuation** — mesmo com ROE 20%+, spread ROE-Ke < 200 bps gera P/VP justo próximo de 1,0x. Bancos BR só geram valor relevante quando ROE > 22% sustentável.
4. **Ciclo de corte de Selic é o catalisador para upside** — sensibilidade mostra -100bps no Rf → +8 p.p. médio no upside.

---

## Próximos passos sugeridos

- [ ] **Substituir estimativas por dados do pipeline** (PDD, OPEX, depósitos) quando o script CVM for refinado
- [ ] **Adicionar cenários**: stress (crise crédito), base (atual), blue-sky (ciclo de corte de juros)
- [ ] **Construir INTR4** (Inter — digital bank BDR): modelo diferenciado com user growth, FCF forward, P/Sales
- [ ] **Construir ITSA4** (Itaúsa — holding): SOTP com participações em Itaú, Alpargatas, Dexco, Copa Energia, NTS + holding discount
- [ ] **Expandir para bancos médios** — BRSR6, BMGB4, BPAN4, PINE4, ABCB4
- [ ] **Gerar teses PDF** (07_VALUATION → 08_RESEARCH) — fase 2

---

## Código gerador

Os 5 workbooks + comparativa são gerados programaticamente para garantir consistência e reprodutibilidade total.
- Script principal: `12_PYTHON/notebooks/build_banks_grandes_valuation.py` → gera os 5 arquivos individuais
- Script comparativa: `12_PYTHON/notebooks/build_comparativa_5_bancos.py` → extrai outputs dos 5 e consolida em dashboard

---

## Histórico de revisões

- **2026-04-17 (v2)** — Enriquecimento completo: DRE_Proj ganhou 5 métricas calculadas efetivas; BP_Proj passou de 5 linhas para Balanço completo com decomposição Ativo/Passivo/PL + reconciliação + Basileia proxy; Múltiplos ganhou seção forward (LPA/VPA/P/L/DY projetados + ROE implícito); nova aba **11.Cenarios** (Stress/Base/Blue-Sky Gordon 1-stage). Zero erros em todas as 5 planilhas. 445 → 606 fórmulas.
- **2026-04-17 (v1)** — Build inicial dos 5 workbooks (ITUB4, BBAS3, BBDC4, SANB11, BPAC11) + comparativa.

---
*Última atualização: 2026-04-17*
