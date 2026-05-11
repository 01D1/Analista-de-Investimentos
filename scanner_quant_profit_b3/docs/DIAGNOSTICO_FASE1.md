# Diagnostico Fase 1 - Scanner Quant Profit + B3

## Escopo

Este diagnostico avalia a arquitetura atual do scanner, com foco em coleta Profit RTD, normalizacao, persistencia SQLite, ranking intraday, COTAHIST, scanners de acoes/opcoes, duplicidades e riscos para evoluir o projeto para um core quantitativo mais robusto.

## Arquitetura Atual

O fluxo atual tem quatro blocos principais:

1. Coleta intraday: o Excel com RTD do Profit e lido pelo coletor, normalizado para campos padronizados e salvo em snapshots.
2. Scanner intraday: o scanner em tempo real calcula metricas simples de range, gap, preco contra abertura e fechamento anterior, depois gera score heuristico.
3. Historico B3: o coletor COTAHIST baixa ZIP/TXT da B3, parseia linhas do layout fixo e grava historico diario no SQLite.
4. Camada analitica: scanners de opcoes, ranking combinado, estrategia `CALL_CONTINUIDADE`, relatorios, backtests e dashboards Streamlit consomem SQLite e CSVs gerados.

## Leitura Profit RTD

O coletor tenta usar `xlwings` primeiro, o que e correto para RTD/DDE porque preserva valores vivos do Excel aberto. Se falhar, usa `openpyxl`, que so le o arquivo salvo em disco.

Riscos:

- o fallback com `openpyxl` pode mascarar RTD parado;
- nao ha validacao explicita de colunas obrigatorias;
- nao ha carimbo de qualidade da leitura, como `source_mode=xlwings/openpyxl`;
- erros de planilha, aba ou Excel fechado podem virar excecao generica.

## Normalizacao

A normalizacao renomeia colunas do Excel para campos internos, converte numeros brasileiros e completa colunas ausentes com `None`.

Pontos fortes:

- campos principais ja estao padronizados;
- valores em formato brasileiro sao tratados.

Riscos:

- nao ha schema formal de entrada;
- campos ausentes seguem para o banco sem alerta de qualidade;
- percentual pode vir como `2.31` ou `0.0231` dependendo da origem e ainda nao ha normalizacao semantica;
- nao ha deduplicacao por ativo/timestamp.

## Snapshots E Banco

O banco atual usa tabelas operacionais como `profit_snapshots`, `realtime_signals`, `cotahist_daily`, `trade_journal` e `options_greeks_snapshot`.

Melhoria ja aplicada:

- `cotahist_daily` passou a ser a tabela principal para COTAHIST;
- `b3_quotes` virou view de compatibilidade para codigo legado;
- ha teste cobrindo o fluxo `cotahist_daily -> b3_quotes`.

Riscos remanescentes:

- ainda nao ha migrations versionadas;
- o schema mistura nomes novos e legados;
- `profit_snapshots` pode crescer sem politica de compactacao;
- nao ha tabelas canonicas para sinais, metricas calculadas, regimes e backtests estatisticos.

## Ranking E Score Atual

O score intraday atual e uma soma fixa de regras:

- preco acima da abertura;
- preco acima do fechamento anterior;
- preco perto da maxima;
- variacao positiva;
- volume financeiro minimo;
- numero de negocios minimo;
- posicao alta dentro do range.

Problemas matematicos:

- score e binario por regra, sem intensidade relativa;
- volume absoluto substitui volume relativo;
- risco nao reduz a nota de forma estruturada;
- volatilidade e gap nao sao tratados como possiveis penalidades;
- nao ha separacao entre momentum, tendencia, liquidez, volatilidade e risco;
- nao ha calibracao historica nem probabilidade observada do sinal.

## Sinais Atuais

A classificacao atual e simples: `COMPRA/FORCA`, `OBSERVAR`, `NEUTRO` ou `FRAQUEZA`.

Riscos:

- linguagem pode soar como recomendacao se nao houver contexto;
- pouca granularidade para mesa quantitativa;
- explicacao textual existe como `motivos`, mas ainda nao e estruturada nem auditavel.

## Historico B3 E Opcoes

O coletor COTAHIST baixa, extrai e parseia o layout fixo da B3. A inferencia de opcoes usa tipo de mercado e prefixo do ticker.

Melhoria ja aplicada:

- parser grava campos compativeis com `cotahist_daily`;
- view `b3_quotes` expoe nomes esperados pelos scanners antigos;
- teste novo valida parser, gravacao e leitura pela estrategia.

Riscos:

- inferencia de ativo-objeto por prefixo de quatro letras pode errar casos especiais;
- COTAHIST nao traz bid/ask intraday nem open interest confiavel no formato atual;
- Greeks dependem de volatilidade implícita/modelo quando IV nao esta observada;
- filtros de opcoes ainda priorizam liquidez basica.

## Estrutura E Duplicidades

Arquivos/pastas que devem ser revisados antes de publicar:

- backups com sufixo `.bak_20260504_110842`;
- subprojeto copiado dentro de `data/scanner_quant/scanner_quant`;
- modulo duplicado em `src/scanners/modulo_conexao_acoes_opcoes`;
- arquivos gerados em `data/database`, `data/raw`, `data/reports`, `data/journal` e `data/realtime`;
- caches Python e pytest.

Nada deve ser apagado sem uma etapa separada de inventario e confirmacao.

## Oportunidades De Evolucao

1. Separar calculo quantitativo puro de coleta, banco e dashboard.
2. Criar tabelas canonicas para sinais, metricas, backtests e regimes.
3. Trocar score unico por score composto auditavel.
4. Adicionar volume relativo, risco, volatilidade e assimetria ao ranking.
5. Criar explicacoes estruturadas para cada sinal.
6. Medir estatistica historica dos sinais antes de qualquer linguagem operacional.
7. Preparar enriquecimento por noticias, valuation, macro e opcoes.

## Plano De Refatoracao Sem Quebrar

1. Manter comandos atuais funcionando.
2. Criar core quantitativo puro em paralelo ao scanner legado.
3. Cobrir o core com testes unitarios.
4. Criar adaptador do scanner legado para chamar o core.
5. Salvar scores novos em colunas/tabelas novas antes de remover campos antigos.
6. Criar migrations simples para novas tabelas.
7. Migrar dashboards para ler as tabelas canonicas.
8. So depois remover duplicidades e backups, com lista aprovada.
