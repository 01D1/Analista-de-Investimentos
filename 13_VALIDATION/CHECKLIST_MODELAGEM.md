---
title: Checklist de Modelagem
tags:
  - validação
  - modelagem
  - checklist
aliases:
  - Checklist Modelo
status: validado
---

# Checklist de Modelagem Financeira

---

## Estrutura do Modelo

- [ ] DRE, BP e DFC estão integrados (ligados por fórmulas, não por valores hardcoded)
- [ ] Inputs separados dos cálculos (área de premissas isolada)
- [ ] Dados históricos claramente separados de projeções

## Ligações entre Demonstrações

- [ ] Lucro Líquido da DRE → ponto de partida da DFC
- [ ] D&A da DRE → adicionado de volta no CFO da DFC
- [ ] Capex do CFI → alimenta variação do Imobilizado no BP
- [ ] Variação de dívida no CFF → alimenta dívida no BP
- [ ] Caixa Final da DFC → Caixa no BP
- [ ] Dividendos no CFF → reduz PL no BP
- [ ] Lucro Líquido → aumenta PL no BP (via lucros retidos)

## Capital de Giro

- [ ] Dias de recebimento: contas a receber / receita × 365
- [ ] Dias de estoque: estoques / CPV × 365
- [ ] Dias de pagamento: fornecedores / CPV × 365
- [ ] NWC = CR + Estoques – Fornecedores
- [ ] Variação de NWC alimenta CFO corretamente

## Depreciação e Capex

- [ ] Depreciação: % do imobilizado bruto ou taxa explícita
- [ ] Capex de manutenção ≥ depreciação (premissa razoável para empresa operacional)
- [ ] Capex de expansão ligado ao crescimento projetado

## Dívida e Juros

- [ ] Despesa financeira calculada sobre saldo médio da dívida do período
- [ ] Amortização de dívida explícita no CFF
- [ ] Novos empréstimos explícitos no CFF

## Sensatez das Projeções

- [ ] Crescimento de receita converge para taxas sustentáveis no final do período
- [ ] Margem EBIT não explode nem desaba sem justificativa
- [ ] FCF não é permanentemente negativo sem razão de expansão

---
*Última atualização: 2026-04-16*
