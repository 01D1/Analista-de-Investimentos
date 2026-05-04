# Arquitetura do Sistema

O sistema é dividido em 4 motores independentes.

## 1. Financial Engine
Responsável por dados financeiros, modelagem, indicadores e valuation.

## 2. Macro News Engine
Responsável por coleta, classificação e interpretação de notícias e eventos macro.

## 3. Intelligence Layer
Responsável por conectar dados financeiros, notícias, setores, riscos e teses.

## 4. Content Engine
Responsável por transformar análise em conteúdo para redes sociais, resumos, relatórios e publicações.

## Regra central
Nenhum módulo deve se misturar estruturalmente com o outro.
A integração ocorre apenas pela camada de inteligência.
