# Estrutura da Noticia

Formato padrao para ingestao e classificacao de noticias macro.

## Campos Obrigatorios

- **Data**: Data de publicacao
- **Fonte**: Origem da noticia (Bloomberg, Reuters, Valor, etc.)
- **Regiao**: Pais ou regiao afetada
- **Tema**: Classificacao tematica (ver TAGGING)
- **Impacto**: Positivo / Negativo / Neutro
- **Sentimento**: Tom geral da noticia
- **Setores afetados**: Quais setores sao impactados
- **Empresas afetadas**: Tickers diretamente relacionados

## Regras

1. Toda noticia deve ser classificada antes de entrar no sistema
2. O campo "Impacto" e uma avaliacao preliminar, nao uma conclusao
3. A conexao com empresas/setores deve ser feita pela Intelligence Layer, nao pelo operador
4. Noticias sem fonte verificavel nao devem ser ingeridas

> Referencia: [[00_META/INTELLIGENCE_SYSTEM/MACRO_NEWS_ENGINE]]
