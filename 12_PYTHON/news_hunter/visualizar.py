# -*- coding: utf-8 -*-
"""
visualizar.py — News Hunter
============================
Consulta e exibe as notícias coletadas no banco de dados.

Modos de uso:
  python visualizar.py               → lista as 20 mais recentes
  python visualizar.py -n 50         → lista as 50 mais recentes
  python visualizar.py -b "selic"    → busca por palavra-chave
  python visualizar.py -c empresas   → filtra por categoria
  python visualizar.py --stats       → estatísticas do banco
  python visualizar.py --hoje        → notícias coletadas hoje
  python visualizar.py --alertas     → notícias com alerta disparado
  python visualizar.py --top         → top notícias de hoje por score
  python visualizar.py --urgentes    → somente notícias urgentes
  python visualizar.py --score-min 6 → filtra score >= 6
  python visualizar.py --abrir 42    → abre o link da notícia ID 42 no browser
"""

import argparse
import sys
import webbrowser
from datetime import datetime, date

import banco
import config

# ── Cores ANSI ────────────────────────────────────────────────────────────────
def _suporta_cores():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

RESET   = "\033[0m"  if _suporta_cores() else ""
NEGRITO = "\033[1m"  if _suporta_cores() else ""
VERDE   = "\033[92m" if _suporta_cores() else ""
AMARELO = "\033[93m" if _suporta_cores() else ""
AZUL    = "\033[94m" if _suporta_cores() else ""
CINZA   = "\033[90m" if _suporta_cores() else ""
VERMELHO= "\033[91m" if _suporta_cores() else ""
CIANO   = "\033[96m" if _suporta_cores() else ""

# Forçar UTF-8 no Windows
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", closefd=False)

LARGURA = 90

def _linha(char="─"):
    print(char * LARGURA)

def _cabecalho(titulo: str):
    _linha("═")
    print(f"{NEGRITO}{AZUL}  {titulo}{RESET}")
    _linha("═")

def _formatar_data(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        hoje = date.today()
        if dt.date() == hoje:
            return f"hoje {dt.strftime('%H:%M')}"
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return iso[:16]

def _truncar(texto: str, maxlen: int) -> str:
    if not texto:
        return ""
    return texto if len(texto) <= maxlen else texto[:maxlen - 1] + "…"

def _cor_categoria(cat: str) -> str:
    cores = {
        "empresas":            VERDE,
        "tecnologia":          CIANO,
        "economia_brasil":     AMARELO,
        "economia_global":     AMARELO,
        "bancos_centrais":     AMARELO,
        "politica_economica":  AMARELO,
        "commodities":         "\033[95m",   # magenta
        "bolsas":              AZUL,
        "criptomoedas":        "\033[33m",   # laranja
        "calendario_economico":AMARELO,
        "geral":               CINZA,
    }
    return cores.get((cat or "").lower(), CINZA)

def _badge_score(score) -> str:
    """Retorna badge colorido pelo score."""
    try:
        s = int(score or 0)
    except (ValueError, TypeError):
        return ""
    if s >= 10:
        return f"{VERMELHO}[{s:>2}]{RESET}"
    elif s >= 6:
        return f"{AMARELO}[{s:>2}]{RESET}"
    elif s >= 3:
        return f"{VERDE}[{s:>2}]{RESET}"
    return f"{CINZA}[{s:>2}]{RESET}"


# ── Exibição ──────────────────────────────────────────────────────────────────

def exibir_lista(rows: list, titulo: str = ""):
    if titulo:
        _cabecalho(titulo)
    if not rows:
        print(f"\n  {CINZA}Nenhuma notícia encontrada.{RESET}\n")
        return

    print(f"\n  {CINZA}{'ID':>5}  {'Score':>5}  {'Data':>10}  {'Cat':12}  Título{RESET}")
    _linha()
    for r in rows:
        id_   = r["id"]
        score = _badge_score(r.get("score", 0))
        data  = _formatar_data(r["data_coleta"])
        cat   = r.get("categoria") or ""
        titulo_n = _truncar(r["titulo"], 55)
        cor   = _cor_categoria(cat)
        alerta = f" {VERMELHO}🚨{RESET}" if r.get("urgente") or r.get("alertado") else ""

        print(f"  {CINZA}{id_:>5}{RESET}  "
              f"{score:>5}  "
              f"{CINZA}{data:>10}{RESET}  "
              f"{cor}{cat:<12}{RESET}  "
              f"{titulo_n}{alerta}")

    _linha()
    print(f"  {CINZA}Total exibido: {len(rows)}{RESET}\n")


def exibir_detalhe(row: dict):
    _linha("═")
    print(f"\n  {NEGRITO}#{row['id']} — {row['titulo']}{RESET}\n")
    print(f"  {CINZA}Fonte:{RESET}        {row.get('fonte', '—')}")
    print(f"  {CINZA}Categoria:{RESET}    {row.get('categoria', '—')} / {row.get('subcategoria', '—')}")
    score = row.get('score', 0)
    print(f"  {CINZA}Score:{RESET}        {_badge_score(score)} {score}")
    print(f"  {CINZA}Urgente:{RESET}      {'🚨 Sim' if row.get('urgente') else 'Não'}")
    print(f"  {CINZA}Publicado:{RESET}    {_formatar_data(row.get('data_pub', ''))}")
    print(f"  {CINZA}Coletado:{RESET}     {_formatar_data(row.get('data_coleta', ''))}")
    print(f"  {CINZA}Link:{RESET}         {AZUL}{row['link']}{RESET}")
    if row.get("motivo_score"):
        print(f"  {CINZA}Motivo score:{RESET} {row['motivo_score'][:80]}")
    if row.get("resumo_curto"):
        print(f"  {CINZA}Resumo:{RESET}       {row['resumo_curto'][:120]}")
    if row.get("alertado"):
        print(f"  {VERMELHO}⚠  Alerta imediato disparado{RESET}")
    if row.get("conteudo"):
        print(f"\n  {CINZA}{'─' * 80}{RESET}")
        trecho = _truncar(row["conteudo"].strip(), 800)
        for i in range(0, len(trecho), 85):
            print("  " + trecho[i:i+85])
    print()
    _linha("═")


def exibir_stats():
    stats = banco.estatisticas()
    _cabecalho("ESTATÍSTICAS DO BANCO")
    print(f"\n  {'Total de notícias:':<32} {VERDE}{stats['total']:,}{RESET}")
    print(f"  {'Coletadas hoje:':<32} {VERDE}{stats['hoje']:,}{RESET}")
    print(f"  {'Erros nas fontes (hoje):':<32} {AMARELO}{stats['erros_hoje']}{RESET}")

    # Stats por categoria com score médio
    cats_stats = banco.estatisticas_por_categoria()
    if cats_stats:
        print(f"\n  {CINZA}Categorias de hoje:{RESET}")
        for row in cats_stats:
            cat   = row.get("categoria") or "?"
            total = row.get("total", 0)
            avg   = row.get("score_medio", 0)
            barra = "█" * min(int(total) // 2, 30)
            cor   = _cor_categoria(cat)
            print(f"    {cor}{cat:<22}{RESET}  {CINZA}{barra}{RESET} {total:>3}  "
                  f"(score médio: {avg})")
    elif stats["por_categoria"]:
        print(f"\n  {CINZA}Por categoria (geral):{RESET}")
        for cat, qtd in sorted(stats["por_categoria"].items(),
                               key=lambda x: x[1], reverse=True):
            barra = "█" * min(qtd // 5, 40)
            cor   = _cor_categoria(cat)
            print(f"    {cor}{cat:<22}{RESET}  {CINZA}{barra}{RESET} {qtd}")

    print()
    _linha()
    print(f"  {CINZA}Banco: {config.ARQUIVO_BANCO} | "
          f"Retenção: {config.MANTER_DIAS} dias | "
          f"Intervalo: {config.INTERVALO_SEGUNDOS}s{RESET}\n")


def modo_interativo():
    _cabecalho("NEWS HUNTER — Modo Interativo")
    print(f"  {CINZA}Comandos: <termo>, :cat <cat>, :stats, :hoje, :top, :urgentes, :sair{RESET}\n")

    while True:
        try:
            entrada = input(f"  {AZUL}busca>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Até logo!\n")
            break

        if not entrada:
            continue
        if entrada.lower() in (":sair", ":exit", "q", "quit"):
            print("\n  Até logo!\n")
            break
        if entrada.lower() == ":stats":
            exibir_stats()
            continue
        if entrada.lower() == ":hoje":
            rows = banco.buscar_hoje()
            exibir_lista(rows, f"Notícias de hoje ({len(rows)})")
            continue
        if entrada.lower() == ":top":
            rows = banco.buscar_top_noticias_hoje(limite=20)
            exibir_lista(rows, f"Top notícias de hoje por score ({len(rows)})")
            continue
        if entrada.lower() == ":urgentes":
            rows = banco.buscar_urgentes(limite=20)
            exibir_lista(rows, f"Notícias urgentes ({len(rows)})")
            continue
        if entrada.lower().startswith(":cat "):
            cat = entrada[5:].strip()
            rows = banco.buscar(categoria=cat, limite=30)
            exibir_lista(rows, f"Categoria: {cat}")
            continue
        if entrada.lower().startswith(":id "):
            try:
                nid = int(entrada[4:].strip())
                rows = banco.buscar_por_id(nid)
                if rows:
                    exibir_detalhe(rows[0])
                else:
                    print(f"  {CINZA}ID {nid} não encontrado.{RESET}\n")
            except ValueError:
                print(f"  {CINZA}Use :id <número>{RESET}\n")
            continue

        palavras = entrada.split()
        rows = banco.buscar(palavras=palavras, limite=25)
        exibir_lista(rows, f'Resultados para "{entrada}"')


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="News Hunter — visualizador de notícias")
    p.add_argument("-n", "--numero",    type=int, default=20,
                   help="Quantidade de notícias a exibir (padrão: 20)")
    p.add_argument("-b", "--busca",     default=None,
                   help="Busca por palavra-chave no título/conteúdo")
    p.add_argument("-c", "--categoria", default=None,
                   help="Filtra por categoria (ex: empresas, bolsas, tecnologia)")
    p.add_argument("--stats",     action="store_true",
                   help="Exibe estatísticas do banco")
    p.add_argument("--hoje",      action="store_true",
                   help="Notícias coletadas hoje")
    p.add_argument("--alertas",   action="store_true",
                   help="Apenas notícias com alerta disparado")
    p.add_argument("--top",       action="store_true",
                   help="Top notícias de hoje ordenadas por score")
    p.add_argument("--urgentes",  action="store_true",
                   help="Apenas notícias marcadas como urgentes")
    p.add_argument("--score-min", type=int, default=0, dest="score_min",
                   help="Filtra notícias com score >= valor informado")
    p.add_argument("--abrir",     type=int, default=None, metavar="ID",
                   help="Abre o link da notícia de dado ID no browser")
    p.add_argument("--detalhe",   type=int, default=None, metavar="ID",
                   help="Exibe o conteúdo completo da notícia de dado ID")
    p.add_argument("-i", "--interativo", action="store_true",
                   help="Modo interativo de busca no terminal")
    args = p.parse_args()

    banco.inicializar()

    if args.interativo:
        modo_interativo()
        return

    if args.stats:
        exibir_stats()
        return

    if args.abrir is not None:
        rows = banco.buscar_por_id(args.abrir)
        if rows:
            url = rows[0]["link"]
            print(f"  Abrindo: {url}")
            webbrowser.open(url)
        else:
            print(f"  ID {args.abrir} não encontrado.")
        return

    if args.detalhe is not None:
        rows = banco.buscar_por_id(args.detalhe)
        if rows:
            exibir_detalhe(rows[0])
        else:
            print(f"  ID {args.detalhe} não encontrado.")
        return

    # ── Modos de listagem ─────────────────────────────────────────────────────
    if args.top:
        rows = banco.buscar_top_noticias_hoje(
            limite=args.numero, score_minimo=args.score_min
        )
        titulo_exib = f"Top {args.numero} notícias de hoje — ordenadas por score"
        if args.score_min:
            titulo_exib += f" (score ≥ {args.score_min})"
        exibir_lista(rows, titulo_exib)
        return

    if args.urgentes:
        rows = banco.buscar_urgentes(limite=args.numero)
        exibir_lista(rows, f"Notícias urgentes ({len(rows)})")
        return

    palavras  = args.busca.split() if args.busca else None
    categoria = args.categoria

    if args.hoje:
        rows_base = banco.buscar_hoje(limite=args.numero * 5)
        # Aplica filtro de score_min se informado
        if args.score_min:
            rows_base = [r for r in rows_base if (r.get("score") or 0) >= args.score_min]
        rows = rows_base[:args.numero]
        titulo_exib = f"Notícias de hoje — {date.today().strftime('%d/%m/%Y')}"
        if args.score_min:
            titulo_exib += f" (score ≥ {args.score_min})"
    elif args.alertas:
        rows = banco.buscar_alertados(limite=args.numero)
        titulo_exib = "Notícias com alerta imediato"
    elif categoria:
        rows = banco.buscar_por_categoria(
            categoria, limite=args.numero, score_minimo=args.score_min
        )
        titulo_exib = f"Categoria: {categoria}"
        if args.score_min:
            titulo_exib += f" | score ≥ {args.score_min}"
    else:
        rows = banco.buscar(palavras=palavras, categoria=categoria,
                            limite=args.numero)
        if args.score_min:
            rows = [r for r in rows if (r.get("score") or 0) >= args.score_min]
        partes = []
        if palavras:
            partes.append(f'busca="{args.busca}"')
        if args.score_min:
            partes.append(f"score≥{args.score_min}")
        titulo_exib = ("Últimas notícias" if not partes
                       else "Notícias — " + " | ".join(partes))

    exibir_lista(rows, titulo_exib)


if __name__ == "__main__":
    main()
