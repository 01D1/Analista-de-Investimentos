---
title: Segurança e Governança
tags:
  - segurança
  - governança
  - credenciais
aliases:
  - Segurança
  - Governança
---

# Segurança e Governança

---

## Credenciais e Variáveis de Ambiente

> [!danger] Nunca versionar credenciais em arquivos `.py`, `.ipynb` ou `.md`

- Todas as chaves de API em `.env` (na raiz do projeto Python)
- `.env` no `.gitignore`
- Usar `python-dotenv` para carregar
- Rotacionar chaves periodicamente

```bash
# .env (não versionar)
CVM_API_URL=https://dados.cvm.gov.br/...
ALPHA_VANTAGE_KEY=...
FMP_API_KEY=...
DB_PATH=./data/financials.duckdb
LOG_LEVEL=INFO
```

---

## Política de Logs

- Logs devem registrar: ação, timestamp, parâmetros de entrada, resultado (sucesso/falha)
- Logs **não** devem conter: chaves de API, senhas, dados pessoais
- Nível padrão: `INFO` em produção, `DEBUG` em desenvolvimento
- Logs de erro devem incluir traceback completo
- Arquivos de log em `12_PYTHON/logs/` — não versionar logs de produção

---

## Scraping Ético

- Respeitar `robots.txt` de cada site
- Adicionar `User-Agent` identificável nas requisições
- Implementar rate limiting (mínimo 1–2s entre requests)
- Não sobrecarregar servidores com requests paralelos massivos
- Preferir APIs oficiais quando disponíveis (ex: CVM dados abertos)

---

## Controle de Acesso

- Vault Obsidian: acesso local, não sincronizar dados sensíveis em nuvem pública sem criptografia
- Código: repositório privado em GitHub
- Dados brutos: não publicar arquivos que contenham dados não públicos

---

## Backups

- Vault Obsidian: backup automático diário (nuvem privada ou disco externo)
- Código: GitHub como backup primário
- Dados processados: snapshot semanal em Parquet com data no nome do arquivo
- Outputs críticos: versionar com data e manter ao menos 3 versões anteriores

---

## Versionamento de Outputs Críticos

Antes de gerar nova versão de valuation ou modelo:
1. Salvar versão atual com data: `AAAA-MM-DD_[empresa]_[tipo]_v[N].md`
2. Mover versão anterior para `25_ARCHIVE/` se muito antiga
3. Registrar mudança em `18_DECISIONS/` se premissas mudaram

---
*Última atualização: 2026-04-16*
