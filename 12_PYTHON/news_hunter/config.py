# -*- coding: utf-8 -*-
"""
config.py — Configurações centrais do News Hunter
Edite aqui sem precisar tocar no código principal.
"""

try:
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import os

# ══════════════════════════════════════════════════════════════════════════════
# ── Coleta ────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# Palavras-chave: salvar só notícias que contenham ao menos uma.
# Deixe [] para salvar tudo.
PALAVRAS_CHAVE = [
    # Investimento / mercado financeiro
    "investimento", "ibovespa", "bolsa", "ações", "fundo",
    "cdi", "tesouro", "dividendos", "valuation", "resultado",
    "lucro", "ebitda", "receita", "balanço", "guidance",
    "ipca", "selic", "copom", "banco central", "juros",
    "câmbio", "dólar", "inflação", "pib", "recessão",
    "crédito", "btg", "itaú", "bradesco", "santander",
    "banco do brasil", "petrobras", "vale", "weg", "ambev",
    "fed", "fomc", "bce", "payroll", "cpi", "treasury",
    "yield", "s&p", "nasdaq", "dow jones", "wall street",
    # Tecnologia
    "tecnologia", "inteligência artificial", "ia", "ai",
    "nvidia", "microsoft", "apple", "google", "meta",
    "amazon", "tesla", "openai", "semicondutores", "chips",
    "big tech", "cloud", "data center", "software",
]

INTERVALO_SEGUNDOS  = 120
EXTRAIR_CONTEUDO    = True
TIMEOUT_REQUISICAO  = 10
MAX_CHARS_CONTEUDO  = 8000
ARQUIVO_BANCO       = "banco.db"
ARQUIVO_FONTES      = "fontes.txt"
ARQUIVO_LOG         = "news_hunter.log"
MANTER_DIAS         = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ══════════════════════════════════════════════════════════════════════════════
# ── Telegram ──────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# Ative e preencha token + chat_id para habilitar envios
TELEGRAM_ATIVO   = os.getenv("TELEGRAM_ATIVO", "true").lower() in ("true", "1", "yes")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN",   "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Enviar boletim automaticamente após gerar
TELEGRAM_ENVIAR_BOLETIM = True

# Tamanho máximo seguro por mensagem (limite real do Telegram é 4096 chars)
TELEGRAM_MAX_CHARS = 4000

# False = envia tudo em uma única mensagem (trunca se passar do limite)
# True  = divide em partes se necessário
TELEGRAM_DIVIDIR_MENSAGEM = False

# Se True, adiciona cabeçalho "Parte X/N" em mensagens divididas
TELEGRAM_PREFIXO_PARTES = True

# Palavras que disparam alerta IMEDIATO pelo Telegram
PALAVRAS_ALERTA_IMEDIATO = [
    "colapso", "crise", "falência", "default", "emergência",
]

# ══════════════════════════════════════════════════════════════════════════════
# ── Agendador ────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# Horários diários para coletar + gerar + enviar (formato "HH:MM")
HORARIOS_ENVIO_TELEGRAM = ["07:30", "12:00", "18:00"]

# Se True, pula sábado e domingo
RODAR_DIAS_UTEIS_APENAS = True

# ══════════════════════════════════════════════════════════════════════════════
# ── Boletim ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

NOME_BOLETIM    = "RESUMÃO DO DIA"
PAIS_BASE       = "Brasil"
FUSO_HORARIO    = "America/Recife"

LIMITE_DESTAQUES              = 3   # top 3 para "VOCÊ PRECISA SABER"
LIMITE_NOTICIAS_BOLETIM       = 8   # top 8 por score para "PRINCIPAIS NOTÍCIAS"
LIMITE_NOTICIAS_POR_CATEGORIA = 5   # por categoria (usado internamente)
LIMITE_ALERTAS                = 3

PASTA_BOLETINS  = "boletins"
PASTA_TEMPLATES = "templates"
TEMPLATE_BOLETIM = "boletim_mercado.j2"

SCORE_MINIMO_BOLETIM        = 6   # exige ao menos 2 matches temáticos ou fonte+tema
SALVAR_NOTICIAS_SCORE_BAIXO = False

# Categorias que aparecem no boletim (remova as que não quer)
CATEGORIAS_BOLETIM = [
    "empresas",
    "tecnologia",
    "economia_brasil",
    "economia_global",
    "bancos_centrais",
    "bolsas",
    "calendario_economico",
    "alerta_forte",
]

# ══════════════════════════════════════════════════════════════════════════════
# ── Fontes e temas prioritários ───────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

FONTES_PRIORITARIAS = [
    "Reuters", "Valor", "InfoMoney", "Brazil Journal", "Exame",
    "CNN Brasil", "G1", "Estadão", "Folha", "BBC", "Financial Times",
    "Bloomberg", "The Wall Street Journal", "CNBC", "MarketWatch",
]

TEMAS_PRIORITARIOS = [
    "empresas", "tecnologia", "economia", "bancos centrais",
    "commodities", "bolsas", "mercado financeiro", "calendário econômico",
]

PALAVRAS_EMPRESAS = [
    "lucro", "receita", "ebitda", "balanço", "resultado", "guidance",
    "dividendos", "jcp", "recompra", "fusão", "aquisição", "ipo",
    "follow-on", "fato relevante", "petrobras", "vale", "itaú",
    "bradesco", "banco do brasil", "santander", "btg", "weg",
    "magazine luiza", "localiza", "eletrobras", "ambev", "raizen",
    "profit warning", "alerta de lucro", "debêntures", "cri", "cra",
    "inadimplência", "provisão", "reestruturação", "spin-off",
    "oferta pública", "tag along", "nasdaq listing", "nyse listing",
]

PALAVRAS_TECNOLOGIA = [
    "tecnologia", "inteligência artificial", "ia", "ai",
    "semicondutores", "chips", "nvidia", "microsoft", "apple",
    "google", "alphabet", "meta", "amazon", "tesla", "openai",
    "cloud", "software", "data center", "big tech",
]

PALAVRAS_MACRO = [
    "selic", "copom", "banco central", "fed", "fomc", "bce",
    "boe", "boj", "pboc", "juros", "inflação", "ipca", "cpi",
    "ppi", "payroll", "pib", "recessão", "crescimento",
    "atividade econômica", "dólar", "câmbio", "fiscal",
    "arcabouço fiscal", "dívida pública",
    "política monetária", "taxa de juros", "corte de juros", "alta de juros",
    "aperto monetário", "afrouxamento monetário", "qe", "qt",
    "superávit", "déficit primário", "resultado primário",
    "spread", "risco país", "embi", "cds",
    "desvalorização cambial", "apreciação cambial", "reservas internacionais",
    "balança comercial", "conta corrente", "balança de pagamentos",
    "nota de crédito", "rating", "downgrade", "upgrade",
]

PALAVRAS_COMMODITIES = [
    "petróleo", "brent", "wti", "minério de ferro", "ouro",
    "soja", "milho", "trigo", "café", "boi gordo",
    "commodities", "opep", "estoques de petróleo", "gás natural",
]

PALAVRAS_BOLSAS = [
    "ibovespa", "bovespa", "bolsa", "ações", "wall street",
    "s&p 500", "nasdaq", "dow jones", "dax", "stoxx",
    "shanghai", "hang seng", "nikkei", "mercado acionário",
    "futuros", "juros futuros", "yield", "treasury",
    "pregão", "fechamento do mercado", "abertura do mercado",
    "fluxo estrangeiro", "investidor estrangeiro", "short selling",
    "volatilidade", "vix", "opções", "derivativos",
    "mercado futuro", "mini dólar", "mini índice",
]

PALAVRAS_CRIPTO = [
    "bitcoin", "ethereum", "cripto", "criptomoedas", "etf de bitcoin",
    "blockchain", "solana", "xrp", "stablecoin",
]

PALAVRAS_CALENDARIO_ECONOMICO = [
    "agenda econômica", "calendário econômico", "decisão de juros",
    "ata do copom", "ata do fomc", "payroll", "cpi", "ppi",
    "ipca", "pib", "vendas no varejo", "produção industrial",
    "estoques de petróleo", "confiança do consumidor",
]

PALAVRAS_ALERTA_FORTE = [
    "crise", "colapso", "falência", "recuperação judicial",
    "default", "calote", "guerra", "ataque", "sanção",
    "emergência", "queda forte", "dispara", "desaba",
    "rombo", "fraude", "intervenção", "circuit breaker",
]

# ── Exclusões do boletim ──────────────────────────────────────────────────────
# Tópicos que, independente do score, NÃO entram no boletim financeiro.
PALAVRAS_EXCLUIR_BOLETIM = [
    # Campeonatos e resultados esportivos
    "brasileirão", "campeonato brasileiro", "campeonato paulista",
    "campeonato carioca", "campeonato mineiro", "campeonato gaúcho",
    "copa do brasil futebol", "champions league", "premier league",
    "bundesliga", "laliga", "serie a italiana", "libertadores",
    "rodada do", "placar", "gol de",
    # Entretenimento / shows / celebridades
    "big brother brasil", "bbb 2", "oscar 202", "grammy 202",
    "reality show", "taylor swift", "show de ", "concerto de ",
    "festival de música", "lady gaga", "beyoncé",
]
