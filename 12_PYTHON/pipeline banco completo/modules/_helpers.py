"""
Helpers compartilhados entre os módulos.
"""
import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger("pipeline.helpers")


def extrair_valores_df(df: pd.DataFrame, codigos: list[str],
                        periodo: str = None) -> float:
    """
    Extrai e soma valores de contas específicas de um DataFrame CVM.
    Função standalone para uso direto.

    Nota sobre CVM DFPs: cada arquivo contém DOIS exercícios (ÚLTIMO e PENÚLTIMO).
    A coluna DT_REFER é a mesma para todos os registros do arquivo, enquanto
    DT_FIM_EXERC varia por período. Aqui usamos ORDEM_EXERC='ÚLTIMO' para
    garantir apenas o exercício corrente; DT_FIM_EXERC serve de fallback.
    """
    if df is None or df.empty:
        return 0.0

    col_cd = next((c for c in df.columns if "CD_CONTA" in c.upper()), None)
    col_vl = next((c for c in df.columns if "VL_CONTA" in c.upper()), None)
    # Prefer DT_FIM_EXERC over DT_REFER (DT_REFER is the same for all rows)
    col_dt = next((c for c in df.columns if "DT_FIM_EXERC" in c.upper()), None)
    if col_dt is None:
        col_dt = next((c for c in df.columns
                       if "DT_FIM" in c.upper() or "DT_REFER" in c.upper()), None)
    col_ordem = next((c for c in df.columns if "ORDEM_EXERC" in c.upper()), None)

    if not col_cd or not col_vl:
        return 0.0

    df_work = df.copy()

    # Filtrar pelo exercício corrente: preferir ORDEM_EXERC='ÚLTIMO', depois data
    if col_ordem and col_ordem in df_work.columns:
        ultimos = df_work[df_work[col_ordem].astype(str).str.upper() == "ÚLTIMO"]
        if not ultimos.empty:
            df_work = ultimos
        # else: fall through to date-based filter

    if periodo and col_dt:
        df_work[col_dt] = pd.to_datetime(df_work[col_dt], errors="coerce")
        target = pd.to_datetime(periodo, errors="coerce")
        if pd.notna(target):
            df_work = df_work[df_work[col_dt] == target]
        elif not df_work.empty:
            df_work = df_work[df_work[col_dt] == df_work[col_dt].max()]

    mask = df_work[col_cd].astype(str).isin([str(c) for c in codigos])
    df_filtrado = df_work[mask].copy()

    if df_filtrado.empty:
        # Busca parcial
        frames = []
        for cod in codigos:
            partial = df_work[df_work[col_cd].astype(str).str.startswith(str(cod))]
            frames.append(partial)
        if frames:
            df_filtrado = pd.concat(frames).drop_duplicates(subset=[col_cd])

    if df_filtrado.empty:
        return 0.0

    try:
        total = pd.to_numeric(df_filtrado[col_vl], errors="coerce").sum()
        return float(total) if pd.notna(total) else 0.0
    except Exception:
        return 0.0


def setup_logging(log_dir, level="INFO"):
    """Configura logging para arquivo e console."""
    import logging
    from pathlib import Path
    from datetime import datetime

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ]
    )
    return logging.getLogger("pipeline")


def formatar_brl(valor: float, sufixo: str = "MM") -> str:
    """Formata valor em R$ com separadores brasileiros."""
    return f"R$ {valor:>12,.0f} {sufixo}"


def cagr(valor_inicial: float, valor_final: float, n_anos: int) -> float:
    """Calcula CAGR."""
    if valor_inicial <= 0 or n_anos <= 0:
        return 0.0
    return (valor_final / valor_inicial) ** (1 / n_anos) - 1
