# 📰 News Hunter

Coletor e classificador de notícias financeiras com geração automática de **boletim diário**.

---

## Instalação

```bash
pip install -r requirements.txt
```

---

## Comandos principais

### Coletar notícias (ciclo único)
```bash
python crawler.py --uma-vez
```

### Gerar boletim do dia
```bash
python gerar_boletim.py
```

### Coletar e gerar boletim em sequência
```bash
python main.py --coletar-e-gerar
```

### Loop contínuo de coleta
```bash
python crawler.py
```

---

## Visualizar notícias

```bash
# Top notícias de hoje por score
python visualizar.py --top

# Somente notícias urgentes
python visualizar.py --urgentes

# Por categoria
python visualizar.py -c empresas
python visualizar.py -c tecnologia
python visualizar.py -c commodities
python visualizar.py -c bolsas
python visualizar.py -c bancos_centrais
python visualizar.py -c criptomoedas

# Com score mínimo
python visualizar.py --top --score-min 6

# Notícias de hoje
python visualizar.py --hoje

# Estatísticas do banco
python visualizar.py --stats

# Busca por palavra-chave
python visualizar.py -b "selic"

# Detalhe de uma notícia
python visualizar.py --detalhe 42
```

---

## Boletim diário

O boletim é gerado automaticamente com esta estrutura:

```
RESUMÃO DO MERCADO 📊🌎
[Data por extenso]
⌛ Faltam X dias para acabar o ano.

🔥 VOCÊ PRECISA SABER
📅 AGENDA ECONÔMICA
🏢 EMPRESAS
💻 TECNOLOGIA
🌎 ECONOMIA, JUROS E BANCOS CENTRAIS
🛢️ COMMODITIES
📈 BOLSAS E MERCADOS
₿ CRIPTOMOEDAS
⚠️ ALERTAS IMPORTANTES
🧭 LEITURA DO MERCADO
📌 FONTES MONITORADAS
```

Os arquivos são salvos em:
```
boletins/boletim_YYYY-MM-DD.md
boletins/boletim_YYYY-MM-DD.txt
```

---

## Personalização

| Arquivo | O que configura |
|---|---|
| `config.py` | Palavras-chave, score mínimo, fontes prioritárias, nome do boletim |
| `fontes.txt` | Lista de feeds RSS monitorados |
| `templates/boletim_mercado.j2` | Layout e emojis do boletim (Jinja2) |
| `dados/calendario_economico.json` | Eventos da agenda econômica |

---

## Calendário econômico

Edite `dados/calendario_economico.json` para adicionar eventos:

```json
[
  {
    "data": "2026-04-30",
    "horario": "19:00",
    "pais": "EUA",
    "indicador": "Decisão de juros do Fed (FOMC)",
    "importancia": "alta",
    "projecao": "não disponível",
    "anterior": "não disponível",
    "atual": "não disponível",
    "fonte": "manual"
  }
]
```

Importância aceita: `alta`, `média`, `baixa`

---

## Categorias reconhecidas pelo classificador

| Categoria | O que inclui |
|---|---|
| `empresas` | Resultados, dividendos, fusões, IPOs |
| `tecnologia` | IA, big tech, semicondutores |
| `economia_brasil` | Selic, COPOM, IPCA, fiscal |
| `economia_global` | Fed, BCE, BOJ, PIB global |
| `bancos_centrais` | Decisões de juros globais |
| `commodities` | Petróleo, ouro, minério, agro |
| `bolsas` | Ibovespa, S&P 500, Nasdaq, índices |
| `criptomoedas` | Bitcoin, Ethereum e cripto em geral |
| `calendario_economico` | Agenda de indicadores |
| `politica_economica` | Fiscal, reformas, regulação |
| `geral` | Demais notícias |

---

## Score de relevância

| Critério | Pontos |
|---|---|
| Fonte prioritária (Reuters, Valor, Bloomberg...) | +3 |
| Tema: empresas | +3 |
| Tema: tecnologia | +3 |
| Tema: macro / bancos centrais | +4 |
| Tema: commodities | +3 |
| Tema: bolsas | +3 |
| Tema: criptomoedas | +2 |
| Tema: calendário econômico | +4 |
| Alerta forte (crise, falência, colapso...) | +5 |

Notícias com **score ≥ 8** são marcadas como **urgentes** automaticamente.

---

## Integração com Telegram

Envie o boletim diário automaticamente para um canal ou chat no Telegram.

### Passo a passo

**1. Criar o bot no Telegram**

Abra o Telegram e converse com [@BotFather](https://t.me/BotFather):
```
/start
/newbot
```
Escolha um nome e um username para o bot. O BotFather fornecerá o **token** (formato: `123456789:ABC-DEF...`).

**2. Descobrir o chat_id**

Envie qualquer mensagem para o seu bot e acesse no navegador:
```
https://api.telegram.org/bot<SEU_TOKEN>/getUpdates
```
Procure o campo `"chat": {"id": ...}` na resposta JSON. Esse é o seu `chat_id`.

> Para grupos: adicione o bot ao grupo, envie uma mensagem mencionando o bot e consulte o mesmo endpoint.

**3. Configurar as credenciais**

Edite `config.py` (ou crie um arquivo `.env` na pasta do projeto):
```python
# Em config.py:
TELEGRAM_ATIVO    = True
TELEGRAM_TOKEN    = "123456789:ABC-DEF..."   # token do BotFather
TELEGRAM_CHAT_ID  = "987654321"              # seu chat_id

# Horários de envio automático (formato HH:MM):
HORARIOS_ENVIO_TELEGRAM = ["07:30", "12:00", "18:00"]
```

Ou via variáveis de ambiente (`.env`):
```
TELEGRAM_TOKEN=123456789:ABC-DEF...
TELEGRAM_CHAT_ID=987654321
```

**4. Testar a conexão**
```bash
python main.py --testar-telegram
```
Se aparecer `✅ Telegram OK`, o bot está configurado corretamente.

**5. Coletar, gerar e enviar manualmente**
```bash
python main.py --coletar-gerar-enviar
```
Executa o ciclo completo: coleta RSS → classifica → gera boletim → envia no Telegram.

**6. Apenas enviar o boletim já gerado**
```bash
python main.py --enviar-telegram
```
Reenvia o boletim do dia atual sem coletar ou reclassificar.

**7. Agendamento automático**
```bash
python agendador.py
```
Roda em loop permanente e envia o boletim nos horários configurados em `HORARIOS_ENVIO_TELEGRAM`. Respeita dias úteis se `RODAR_DIAS_UTEIS_APENAS = True`.

Para testar imediatamente (sem aguardar o horário):
```bash
python agendador.py --simular
```

**8. Agendar no Windows (inicialização automática)**

Crie uma tarefa no Agendador de Tarefas para rodar o agendador ao iniciar o Windows:
```bash
schtasks /create /tn "NewsHunterTelegram" /tr "python C:\caminho\para\news_hunter\agendador.py" /sc ONSTART /ru SYSTEM /f
```
Ou configure para um horário fixo (ex: 07:00 todos os dias):
```bash
schtasks /create /tn "NewsHunterTelegram" /tr "python C:\caminho\para\news_hunter\agendador.py" /sc DAILY /st 07:00 /f
```

---

### Regras de segurança do envio

- Mensagens longas são divididas automaticamente em partes (máximo `TELEGRAM_MAX_CHARS` por parte)
- Falhas no envio **não interrompem** a geração dos arquivos `.md` e `.txt`
- Intervalo de 1,5s entre partes para respeitar o limite de 20 msg/min do Telegram
- Cada parte é prefixada com `(1/3)`, `(2/3)` etc. quando `TELEGRAM_PREFIXO_PARTES = True`

---

### Comandos Telegram — resumo

| Comando | O que faz |
|---|---|
| `python main.py --testar-telegram` | Verifica se o bot responde |
| `python main.py --enviar-telegram` | Envia o boletim de hoje |
| `python main.py --coletar-gerar-enviar` | Ciclo completo: coleta + boletim + envio |
| `python agendador.py` | Loop com envio nos horários configurados |
| `python agendador.py --simular` | Executa o job imediatamente (teste) |

---

## Estrutura completa de arquivos

```
news_hunter/
├── crawler.py              # Coletor RSS + classificação
├── banco.py                # Acesso ao SQLite
├── classificador.py        # Classificação por regras
├── gerar_boletim.py        # Gerador do boletim diário
├── calendario_economico.py # Módulo de agenda econômica
├── telegram_client.py      # Cliente Telegram (envio)
├── agendador.py            # Agendador automático
├── main.py                 # Orquestrador CLI
├── visualizar.py           # Consultas no terminal
├── config.py               # Configurações centrais
├── fontes.txt              # Feeds RSS monitorados
├── requirements.txt        # Dependências Python
├── banco.db                # Banco SQLite (não apagar)
├── news_hunter.log         # Log de execução
├── boletins/               # Boletins gerados (.md e .txt)
├── templates/              # Templates Jinja2
│   └── boletim_mercado.j2
└── dados/                  # Dados de suporte
    └── calendario_economico.json
```

---

---

## Projetos Relacionados

- [[12_PYTHON/Projetos Implementados|Hub — Projetos Python Implementados]]
- [[scanner_quant_profit_b3/README_OBSIDIAN|Scanner Quant Profit + B3]] — os alertas de notícias deste projeto explicam movimentos captados pelo scanner em tempo real
- [[12_PYTHON/pipeline banco completo/README|Pipeline Banco Completo]] — notícias sobre Selic, resultados e macro alimentam as premissas do valuation

---

*News Hunter — Sistema de Análise de Investimentos*
*Última atualização: 2026-05-03*
