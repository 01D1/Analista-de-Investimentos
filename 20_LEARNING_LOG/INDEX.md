---
title: Diário de Aprendizado
tags:
  - aprendizado
  - log
  - evolução
aliases:
  - Learning Log
  - Diário de Aprendizado
---

# Diário de Aprendizado

> Registro contínuo do que o projeto aprende ao operar.

---

## Como Registrar

Criar entrada com o formato:

```markdown
## AAAA-MM-DD — [Título do Aprendizado]

**Categoria:** biblioteca / fonte / contabilidade / valuation / arquitetura / setor
**Contexto:** onde/como surgiu
**Aprendizado:** o que foi aprendido
**Aplicação futura:** como isso vai mudar a forma de operar
**Linkar para:** skill, workflow ou heurística afetada
```

---

## Categorias

- `biblioteca` — nova biblioteca ou ferramenta útil
- `fonte` — nova fonte de dados ou nuance de fonte existente
- `contabilidade` — armadilha ou peculiaridade contábil
- `valuation` — metodologia, benchmark ou erro de abordagem
- `arquitetura` — melhoria de design do sistema ou código
- `setor` — insight setorial importante

---

## Log

### 2026-04-16 — Estrutura inicial do vault criada

**Categoria:** arquitetura
**Contexto:** Criação do segundo cérebro para o projeto de inteligência financeira.
**Aprendizado:** Um vault de segundo cérebro para este tipo de projeto precisa de 5 camadas distintas (conhecimento, dados, modelagem, inteligência, entrega) para funcionar bem. Misturar essas camadas causa confusão de responsabilidades.
**Aplicação futura:** Sempre checar em qual camada uma nova nota ou módulo pertence antes de criar.
**Linkar para:** [[00_META/ARQUITETURA_DO_CONHECIMENTO]]

---

### 2026-04-16 — Pipeline de Bancos: Erros e Soluções

**Categoria:** fonte / arquitetura
**Contexto:** Construção do pipeline completo de extração de DFPs para 12 bancos brasileiros (ITUB4, BBAS3, BBDC4, SANB11, BPAC11, INTR4, BRSR6, ABCB4, BMGB4, BPAN4, PINE4, ITSA4).

**Aprendizados:**

1. `DFPParser` retorna colunas normalizadas (`account_code`, `account_name`, `value`), não o formato bruto CVM. Qualquer mapper downstream precisa detectar o formato automaticamente via duck typing nas colunas.

2. **PL de bancos: código vs. nome.** Layout varia: Itaú usa `2.08`, BB usa `2.07`, ITSA4 usa `2.03`. Solução: usar o nome da conta (`"patrimônio líquido consolidado"`) com prioridade sobre o código para campos ambíguos (`NAME_PRIORITY_FIELDS`).

3. **Armadilha do código `2.07` no Itaú.** Itaú tem `2.07 = "Passivos sobre Ativos Descontinuados" = 0`. Mapear `2.07 → total_equity` para suportar BB corrompe o Itaú (first-wins, 0 sobrescreve 177bi). Solução: remover `2.07` do mapa de código; confiar apenas no nome.

4. **`net_income = 0` em bancos sem minoritários.** ABCB4, BPAN4: colocam tudo em `3.11` (consolidado), `3.11.01 = 0`. Fallback: `if net_income == 0 and net_income_consolidated != 0: net_income = net_income_consolidated`.

5. **DFC key errada.** `bank_parser` chamava `mapped.get("DFC_MI")` mas `DFPParser` retorna chave `"DFC"`. Erro silencioso: cashflow ficava `None` sem mensagem de erro.

**Aplicação futura:** Ao adicionar novos bancos, verificar o layout de PL na DFP antes de assumir `2.08`. O mapeamento por nome é mais robusto para campos de equity.

**Linkar para:** [[../12_PYTHON/src/normalization/bank_account_mapper]], [[../17_MEMORY/Padroes_identificados]]

---

### 2026-04-16 — Bancos Brasileiros: Diferenças de Análise vs. Industriais

**Categoria:** contabilidade / valuation
**Contexto:** Adaptação do framework de análise industrial para bancos.

**Aprendizados:**

1. **3.01 para bancos ≠ Receita Líquida.** `3.01 = Receitas da Intermediação Financeira` inclui receitas brutas. Não usar como proxy de "top line" para comparação com industriais.

2. **A métrica central de banco é o NII** (Net Interest Income = `3.03` no CVM). Equivale ao Resultado Bruto da Intermediação Financeira (após PDD). O spread bancário é calculado sobre o NII, não sobre o total de intermediação.

3. **ROE é a principal métrica comparativa.** Para comparar bancos de tamanhos diferentes, ROE elimina o efeito do capital regulatório e do mix de funding. ROIC não é diretamente aplicável (banco não tem "capital investido" delimitável da mesma forma).

4. **Alavancagem em bancos é esperada e regulada.** Leverage de 8–12x assets/equity é normal (Basileia III). Não usar os mesmos thresholds de alavancagem de industriais.

5. **BPAC11 (BTG) é único.** É "banco + gestora + advisory + corporate lending". Métricas de banco tradicional (spread de crédito, NIM) são menos representativas. Foco em: receitas por segmento, eficiência por linha de negócio, capital próprio aplicado.

6. **ITSA4 não é banco.** Holding pura com investimentos financeiros. `total_financial_revenues` na prática é dividendos + equivalência patrimonial de Itaú+outros. Não comparar com bancos.

**Aplicação futura:** Ao construir a tabela comparativa de bancos, usar ROE, Eficiência, NIM Proxy e Índice de PDD/Carteira como métricas padrão — não EBITDA ou ROIC.

**Linkar para:** [[../04_GOVERNANCA/FRAMEWORK_GERAL_DE_GOVERNANCA]], [[../03_COMPANIES/ITUB4/DADOS_HISTORICOS]]

---

### 2026-04-17 — Valuation DDM de Bancos: 5 Aprendizados Críticos

**Categoria:** valuation / setor
**Contexto:** Construção de 5 modelos DDM (Gordon 2 estágios) para ITUB4, BBAS3, BBDC4, SANB11 e BPAC11 — outputs em `07_VALUATION/BANCOS_GRANDES/` e comparativa consolidada `COMPARATIVA_BANCOS_5.xlsx`.

**Aprendizados:**

1. **CAPM no Brasil — cuidado com double-counting de risco-país.** A fórmula clássica "Rf_local + β·ERP + CRP" está errada quando usamos ERP_Brasil da Damodaran, porque este já embute o spread soberano (EMBI+). A fórmula correta no Brasil é **Ke = Rf_BR + β·ERP_BR**. Se ignorado, Ke infla ~2 p.p. e todos os preços-alvo ficam artificialmente baixos. Só somar CRP se partir de Rf_US. Guardado em auto-memória do assistente.

2. **DDM Gordon 2 estágios penaliza bancos fee-heavy com baixo payout.** Para BPAC11, payout 30% deixa a maior parte do valor em retained earnings que reinvestem a ROE 20%+, mas o DDM só desconta dividendos distribuídos. Resultado: fair value ~P/VP 0,6x quando o mercado paga P/VP 1,5x. **Correção prática**: usar "payout efetivo total" (dividendos + JCP + recompras) — para BPAC subiu de 30% para 45%, melhorando o alvo de R$ 14,18 → R$ 24,83 (-41,6% vs -61%). Para casos extremos, preferir **Residual Income Model** ou **P/VP implícito Gordon** direto: P/VP = (ROE-g)/(Ke-g).

3. **Template "NIM × Ativos" quebra para bancos de investimento.** BPAC11 tem receita relevante fora da margem financeira clássica (IB, Asset Mgmt, Sales & Trading, Wealth Mgmt). O pipeline CVM não desagrega "Tarifas" por linha de negócio, subestimando fees. **Workaround**: (a) reconciliar tarifas históricas top-down pela diferença entre LL real e LL computado via NIM; (b) projetar NIM como "return on assets total" (5-5,4%) incluindo trading book, não NIM clássico; (c) no futuro, modelar BPAC por segmentos separados (corp lending / IB / AM / WM).

4. **Ke 18-19% no Brasil comprime valuation estruturalmente.** Mesmo com ROE sustentável de 20%+, spread ROE-Ke < 200 bps gera P/VP justo Gordon próximo de 1,0x. Isso explica por que bancos BR historicamente negociam P/VP 1,0-1,5x enquanto bancos US negociam 1,5-2,5x: o Ke maior aqui (Selic alta) consome o prêmio de crescimento. **Consequência**: bancos BR só entregam valuation atraente quando (a) Ke cai via corte de Selic OU (b) ROE sustentável > 22%.

5. **Sensibilidade ao ciclo Selic é altíssima.** Tabela 2D nas abas `9.Sensibilidade`: -100 bps no Rf move o upside médio em +8 p.p. Isso sinaliza que a tese do setor bancário BR é, no fundo, uma tese de **ciclo monetário** — comprar quando Selic está no topo, vender quando está no fundo. O ROE absoluto importa menos que o gap ROE-Ke, e Ke depende diretamente de Rf.

**Outputs gerados (2026-04-17):**
- 5 workbooks `VALUATION_{TICKER}_2026.xlsx` (10 abas cada, 445 fórmulas, 0 erros)
- `COMPARATIVA_BANCOS_5.xlsx` — 7 abas: Resumo, LL Projetado, Múltiplos, Premissas, Balanço, Ranking, Dashboard (com gráficos)
- Scripts versionados em `12_PYTHON/notebooks/`

**Ranking agregado final:** 1º ITUB4 (NEUTRO-, único com operação sólida ao preço atual) → 2º BPAC11 → 3º SANB11 → 4º BBAS3 → 5º BBDC4 (SELL com -48% downside, deterioração estrutural 2020-2024).

**Aplicação futura:**
- Nas próximas teses bancárias, **começar pela sensibilidade Ke/g**, não pelo alvo pontual — o investidor quer saber "em que cenário macro isso vira compra".
- Adicionar **Residual Income Model** como checagem cruzada do DDM para bancos com payout < 40%.
- Para INTR4 (próximo na fila): **NÃO** usar DDM — é digital bank em fase de growth, usar FCF forward + P/Sales.
- Para ITSA4: SOTP (soma das partes), não modelo de banco.

**Linkar para:** [[../07_VALUATION/BANCOS_GRANDES/INDEX]], [[../07_VALUATION/INDEX]], [[../17_MEMORY/Padroes_identificados]]

---
*Última atualização: 2026-04-17*
