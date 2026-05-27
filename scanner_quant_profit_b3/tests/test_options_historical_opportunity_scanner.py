"""
Testes — Historical Opportunity Scanner
=========================================
Todos os testes rodam SEM banco real (apenas mocks).

Cobertura:
1.  test_categorizar_vencimento
2.  test_classificar_moneyness
3.  test_liquidez_score
4.  test_calcular_score
5.  test_classificar_cenario
6.  test_classificar_status
7.  test_run_historical_scanner_sem_banco
8.  test_run_historical_scanner_com_mock
9.  test_output_csv_cols
10. test_estruturas_por_cenario
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ── Import do módulo sob teste ───────────────────────────────────────────────
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.options.historical_opportunity_scanner import (
    ATIVOS_MONITORADOS,
    ESTRUTURAS_POR_CENARIO,
    MIN_LIQUIDEZ_CANDIDATA,
    MIN_LIQUIDEZ_RTD,
    MIN_LIQUIDEZ_SCORE,
    WATCHLIST_COLS,
    CenarioHistorico,
    OportunidadeHistorica,
    StatusOportunidade,
    _calcular_score,
    _categorizar_vencimento,
    _classificar_cenario,
    _classificar_moneyness,
    _classificar_status,
    _classificar_tendencia,
    _liquidez_score,
    run_historical_scanner,
)

# ─────────────────────────────────────────────────────────────────────────────
# 1. test_categorizar_vencimento
# ─────────────────────────────────────────────────────────────────────────────


class TestCategorizarVencimento:
    def test_curto_limite_inferior(self):
        assert _categorizar_vencimento(1) == "CURTO"

    def test_curto_limite_superior(self):
        assert _categorizar_vencimento(30) == "CURTO"

    def test_medio(self):
        assert _categorizar_vencimento(31) == "MEDIO"
        assert _categorizar_vencimento(60) == "MEDIO"
        assert _categorizar_vencimento(90) == "MEDIO"

    def test_longo(self):
        assert _categorizar_vencimento(91) == "LONGO"
        assert _categorizar_vencimento(180) == "LONGO"

    def test_extra_longo(self):
        assert _categorizar_vencimento(181) == "EXTRA_LONGO"
        assert _categorizar_vencimento(365) == "EXTRA_LONGO"

    def test_expirado(self):
        assert _categorizar_vencimento(0) == "EXPIRADO"
        assert _categorizar_vencimento(-5) == "EXPIRADO"


# ─────────────────────────────────────────────────────────────────────────────
# 2. test_classificar_moneyness
# ─────────────────────────────────────────────────────────────────────────────


class TestClassificarMoneyness:
    # CALL: moneyness = (spot - strike) / strike
    def test_call_deep_itm(self):
        # spot=50, strike=40 → (50-40)/40 = 0.25 > 0.10 → DEEP_ITM
        val, cat = _classificar_moneyness(50.0, 40.0, "CALL")
        assert cat == "DEEP_ITM"
        assert val == pytest.approx(0.25, rel=1e-4)

    def test_call_itm(self):
        # spot=50, strike=46 → (50-46)/46 ≈ 0.087 → ITM
        val, cat = _classificar_moneyness(50.0, 46.0, "CALL")
        assert cat == "ITM"

    def test_call_atm(self):
        # spot=50, strike=50 → 0 → ATM
        val, cat = _classificar_moneyness(50.0, 50.0, "CALL")
        assert cat == "ATM"
        assert val == pytest.approx(0.0, abs=1e-6)

    def test_call_otm(self):
        # spot=50, strike=54 → (50-54)/54 ≈ -0.074 → OTM
        val, cat = _classificar_moneyness(50.0, 54.0, "CALL")
        assert cat == "OTM"
        assert val < 0

    def test_call_deep_otm(self):
        # spot=50, strike=65 → (50-65)/65 ≈ -0.23 → DEEP_OTM
        val, cat = _classificar_moneyness(50.0, 65.0, "CALL")
        assert cat == "DEEP_OTM"

    # PUT: moneyness = (strike - spot) / strike
    def test_put_deep_itm(self):
        # spot=40, strike=50 → (50-40)/50 = 0.20 > 0.10 → DEEP_ITM
        val, cat = _classificar_moneyness(40.0, 50.0, "PUT")
        assert cat == "DEEP_ITM"

    def test_put_itm(self):
        # spot=46, strike=50 → (50-46)/50 = 0.08 → ITM
        val, cat = _classificar_moneyness(46.0, 50.0, "PUT")
        assert cat == "ITM"

    def test_put_atm(self):
        val, cat = _classificar_moneyness(50.0, 50.0, "PUT")
        assert cat == "ATM"

    def test_put_otm(self):
        # spot=54, strike=50 → (50-54)/50 = -0.08 → OTM
        val, cat = _classificar_moneyness(54.0, 50.0, "PUT")
        assert cat == "OTM"

    def test_put_deep_otm(self):
        # spot=65, strike=50 → (50-65)/50 = -0.30 → DEEP_OTM
        val, cat = _classificar_moneyness(65.0, 50.0, "PUT")
        assert cat == "DEEP_OTM"

    def test_strike_zero_retorna_atm(self):
        val, cat = _classificar_moneyness(50.0, 0.0, "CALL")
        assert cat == "ATM"
        assert val == 0.0

    def test_case_insensitive(self):
        _, cat_lower = _classificar_moneyness(50.0, 50.0, "call")
        assert cat_lower == "ATM"
        _, cat_upper = _classificar_moneyness(50.0, 50.0, "PUT")
        assert cat_upper == "ATM"


# ─────────────────────────────────────────────────────────────────────────────
# 3. test_liquidez_score
# ─────────────────────────────────────────────────────────────────────────────


class TestLiquidezScore:
    def test_zero_volume_zero_negocios(self):
        assert _liquidez_score(0.0, 0.0) == 0.0

    def test_volume_maximo_sem_negocios(self):
        # vol_5d = 100_000 → 60 pts; negocios = 0 → 0 pts
        assert _liquidez_score(100_000, 0.0) == pytest.approx(60.0)

    def test_sem_volume_negocios_maximo(self):
        # vol = 0 → 0; negocios = 10 → 40 pts
        assert _liquidez_score(0.0, 10.0) == pytest.approx(40.0)

    def test_score_maximo(self):
        # vol=100_000 e negocios=10 → 100.0
        assert _liquidez_score(100_000, 10.0) == pytest.approx(100.0)

    def test_score_intermediario(self):
        # vol=50_000 → 30 pts; negocios=5 → 20 pts → 50.0
        score = _liquidez_score(50_000, 5.0)
        assert score == pytest.approx(50.0)

    def test_volume_acima_cap_nao_extrapola(self):
        # volume 10x acima do cap não passa de 60 pts
        score = _liquidez_score(1_000_000, 0.0)
        assert score == pytest.approx(60.0)

    def test_negocios_acima_cap_nao_extrapola(self):
        score = _liquidez_score(0.0, 100.0)
        assert score == pytest.approx(40.0)

    def test_retorna_float(self):
        result = _liquidez_score(50_000, 5)
        assert isinstance(result, float)


# ─────────────────────────────────────────────────────────────────────────────
# 4. test_calcular_score
# ─────────────────────────────────────────────────────────────────────────────


class TestCalcularScore:
    def test_score_maximo_ideal(self):
        # liq=100 → 30; ATM→20; CURTO→20; RECUPERACAO→20; vol_relativa=0.6→10 = 100
        score = _calcular_score(
            liq_score=100.0,
            moneyness_cat="ATM",
            categoria_vencimento="CURTO",
            cenario=CenarioHistorico.RECUPERACAO_APOS_QUEDA,
            retorno_21d=-0.10,
            vol_relativa=0.6,
        )
        assert score == pytest.approx(100.0)

    def test_score_zero_iliquido(self):
        # liq=0 → 0; DEEP_OTM → 5; EXTRA_LONGO → 5; SEM_ASSIMETRIA → 0; vol=0 → 0
        score = _calcular_score(
            liq_score=0.0,
            moneyness_cat="DEEP_OTM",
            categoria_vencimento="EXTRA_LONGO",
            cenario=CenarioHistorico.SEM_ASSIMETRIA,
            retorno_21d=0.0,
            vol_relativa=0.0,
        )
        assert score == pytest.approx(10.0)  # 0 + 5 + 5 + 0 + 0 = 10

    def test_cenario_bom_vale_mais(self):
        score_bom = _calcular_score(
            50.0, "ATM", "MEDIO",
            CenarioHistorico.CONTINUACAO_ALTA, 0.05, 0.1,
        )
        score_ruim = _calcular_score(
            50.0, "ATM", "MEDIO",
            CenarioHistorico.LATERALIDADE, 0.05, 0.1,
        )
        assert score_bom > score_ruim

    def test_sem_assimetria_nao_adiciona_pontos_cenario(self):
        score = _calcular_score(
            50.0, "ATM", "MEDIO",
            CenarioHistorico.SEM_ASSIMETRIA, 0.0, 0.0,
        )
        # liq=50*0.30=15; ATM=20; MEDIO=15; SEM_ASSIMETRIA=0; vol=0 → 50
        assert score == pytest.approx(50.0)

    def test_vol_relativa_media_vale_5_pts(self):
        score_alta = _calcular_score(50.0, "OTM", "CURTO", CenarioHistorico.LATERALIDADE, 0.0, 0.6)
        score_media = _calcular_score(50.0, "OTM", "CURTO", CenarioHistorico.LATERALIDADE, 0.0, 0.3)
        score_baixa = _calcular_score(50.0, "OTM", "CURTO", CenarioHistorico.LATERALIDADE, 0.0, 0.1)
        assert score_alta > score_media > score_baixa

    def test_score_nao_excede_100(self):
        score = _calcular_score(100.0, "ATM", "CURTO", CenarioHistorico.CONTINUACAO_ALTA, 0.0, 1.0)
        assert score <= 100.0

    def test_retorna_float(self):
        score = _calcular_score(50.0, "ATM", "CURTO", CenarioHistorico.CONTINUACAO_ALTA, 0.0, 0.3)
        assert isinstance(score, float)


# ─────────────────────────────────────────────────────────────────────────────
# 5. test_classificar_cenario
# ─────────────────────────────────────────────────────────────────────────────


class TestClassificarCenario:
    def test_recuperacao_apos_queda(self):
        cenario = _classificar_cenario(
            retorno_5d=-0.02,   # > -3%
            retorno_21d=-0.10,  # < -8%
            vol_hist_21d=0.30,
            vol_relativa=0.0,
            tendencia="LATERAL",
        )
        assert cenario == CenarioHistorico.RECUPERACAO_APOS_QUEDA

    def test_continuacao_alta(self):
        cenario = _classificar_cenario(
            retorno_5d=0.03,    # > 2%
            retorno_21d=0.05,   # > 0%
            vol_hist_21d=0.20,
            vol_relativa=0.1,
            tendencia="ALTA_MODERADA",
        )
        assert cenario == CenarioHistorico.CONTINUACAO_ALTA

    def test_continuacao_baixa(self):
        cenario = _classificar_cenario(
            retorno_5d=-0.03,   # < -2%
            retorno_21d=-0.06,  # < -4%
            vol_hist_21d=0.25,
            vol_relativa=0.2,
            tendencia="BAIXA_MODERADA",
        )
        assert cenario == CenarioHistorico.CONTINUACAO_BAIXA

    def test_protecao_carteira(self):
        # Para acionar PROTECAO_CARTEIRA é preciso que:
        # 1. Não seja RECUPERACAO_APOS_QUEDA (retorno_21d<-8% e retorno_5d>-3%)
        # 2. Não seja CONTINUACAO_ALTA (retorno_5d>2% e retorno_21d>0%)
        # 3. Não seja CONTINUACAO_BAIXA (retorno_5d<-2% e retorno_21d<-4%)
        #    → logo retorno_5d deve estar entre -2% e 0% para não acionar CONTINUACAO_BAIXA
        # 4. retorno_21d < -6%
        cenario = _classificar_cenario(
            retorno_5d=-0.01,   # entre -2% e 0% → não aciona CONTINUACAO_BAIXA
            retorno_21d=-0.07,  # < -6% → aciona PROTECAO_CARTEIRA
            vol_hist_21d=0.25,
            vol_relativa=0.0,
            tendencia="BAIXA_MODERADA",
        )
        assert cenario == CenarioHistorico.PROTECAO_CARTEIRA

    def test_renda_com_ativo(self):
        cenario = _classificar_cenario(
            retorno_5d=0.005,
            retorno_21d=0.01,
            vol_hist_21d=0.20,   # < 0.25
            vol_relativa=0.05,
            tendencia="LATERAL",
        )
        assert cenario == CenarioHistorico.RENDA_COM_ATIVO

    def test_volatilidade_em_alta(self):
        cenario = _classificar_cenario(
            retorno_5d=-0.01,
            retorno_21d=-0.02,
            vol_hist_21d=0.40,   # > 0.35
            vol_relativa=0.60,   # > 0.5
            tendencia="ALTA_MODERADA",
        )
        assert cenario == CenarioHistorico.VOLATILIDADE_EM_ALTA

    def test_lateralidade(self):
        cenario = _classificar_cenario(
            retorno_5d=0.005,
            retorno_21d=0.01,
            vol_hist_21d=0.30,   # >= 0.25 → não é RENDA_COM_ATIVO
            vol_relativa=0.1,
            tendencia="LATERAL",
        )
        assert cenario == CenarioHistorico.LATERALIDADE

    def test_sem_assimetria(self):
        cenario = _classificar_cenario(
            retorno_5d=0.01,
            retorno_21d=0.01,
            vol_hist_21d=0.20,
            vol_relativa=0.1,
            tendencia="ALTA_MODERADA",   # Não é LATERAL
        )
        assert cenario == CenarioHistorico.SEM_ASSIMETRIA

    def test_recuperacao_tem_prioridade_sobre_protecao(self):
        # retorno_21d = -0.09 e retorno_5d = -0.01 → deve ser RECUPERACAO
        cenario = _classificar_cenario(
            retorno_5d=-0.01,
            retorno_21d=-0.09,
            vol_hist_21d=0.25,
            vol_relativa=0.0,
            tendencia="LATERAL",
        )
        assert cenario == CenarioHistorico.RECUPERACAO_APOS_QUEDA


# ─────────────────────────────────────────────────────────────────────────────
# 6. test_classificar_status
# ─────────────────────────────────────────────────────────────────────────────


class TestClassificarStatus:
    def test_descartar_iliquida_quando_score_baixo(self):
        status, motivo = _classificar_status(5.0, CenarioHistorico.CONTINUACAO_ALTA, "CURTO")
        assert status == StatusOportunidade.DESCARTAR_ILIQUIDA
        assert "Liquidez" in motivo or "liquidez" in motivo.lower()

    def test_descartar_sem_assimetria(self):
        status, motivo = _classificar_status(50.0, CenarioHistorico.SEM_ASSIMETRIA, "CURTO")
        assert status == StatusOportunidade.DESCARTAR_SEM_ASSIMETRIA

    def test_candidata_proximo_pregao(self):
        status, motivo = _classificar_status(
            MIN_LIQUIDEZ_CANDIDATA, CenarioHistorico.CONTINUACAO_ALTA, "CURTO"
        )
        assert status == StatusOportunidade.CANDIDATA_PROXIMO_PREGAO

    def test_candidata_requer_vencimento_curto(self):
        # liquidez alta mas vencimento MEDIO → não é candidata
        status, motivo = _classificar_status(
            MIN_LIQUIDEZ_CANDIDATA, CenarioHistorico.CONTINUACAO_ALTA, "MEDIO"
        )
        assert status == StatusOportunidade.MONITORAR_NO_RTD

    def test_monitorar_no_rtd(self):
        status, motivo = _classificar_status(
            MIN_LIQUIDEZ_RTD, CenarioHistorico.CONTINUACAO_ALTA, "MEDIO"
        )
        assert status == StatusOportunidade.MONITORAR_NO_RTD

    def test_aguardar_liquidez(self):
        # score entre MIN_LIQUIDEZ_SCORE (10) e MIN_LIQUIDEZ_RTD (30)
        status, motivo = _classificar_status(
            20.0, CenarioHistorico.CONTINUACAO_ALTA, "CURTO"
        )
        assert status == StatusOportunidade.AGUARDAR_LIQUIDEZ

    def test_score_exatamente_no_limite_candidata(self):
        status, _ = _classificar_status(
            MIN_LIQUIDEZ_CANDIDATA, CenarioHistorico.RECUPERACAO_APOS_QUEDA, "CURTO"
        )
        assert status == StatusOportunidade.CANDIDATA_PROXIMO_PREGAO

    def test_score_exatamente_no_limite_rtd(self):
        status, _ = _classificar_status(
            MIN_LIQUIDEZ_RTD, CenarioHistorico.RECUPERACAO_APOS_QUEDA, "LONGO"
        )
        assert status == StatusOportunidade.MONITORAR_NO_RTD

    def test_iliquida_tem_prioridade_sobre_sem_assimetria(self):
        # Score < 10 deve retornar DESCARTAR_ILIQUIDA mesmo se cenário=SEM_ASSIMETRIA
        status, _ = _classificar_status(5.0, CenarioHistorico.SEM_ASSIMETRIA, "CURTO")
        assert status == StatusOportunidade.DESCARTAR_ILIQUIDA


# ─────────────────────────────────────────────────────────────────────────────
# 7. test_run_historical_scanner_sem_banco
# ─────────────────────────────────────────────────────────────────────────────


class TestRunSemBanco:
    def test_retorna_dataframe_vazio_quando_banco_inexistente(self, tmp_path):
        db_inexistente = tmp_path / "nao_existe.db"
        result = run_historical_scanner(db_path=db_inexistente, ativos=["PETR4"])
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ─────────────────────────────────────────────────────────────────────────────
# 8. test_run_historical_scanner_com_mock
# ─────────────────────────────────────────────────────────────────────────────


def _criar_banco_mock(db_path: Path) -> None:
    """
    Cria banco SQLite temporário com dados mínimos para teste.
    - Spot PETR4 com 30 pregões
    - Opções CALL (070) e PUT (080) com liquidez suficiente
    - Um registro com market_type='020' (deve ser excluído)
    """
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE cotahist_daily (
            trade_date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            market_type TEXT,
            bdi_code TEXT,
            company_name TEXT,
            specification TEXT,
            term_days TEXT,
            open REAL,
            high REAL,
            low REAL,
            average REAL,
            close REAL,
            best_bid REAL,
            best_ask REAL,
            trades INTEGER,
            quantity REAL,
            volume REAL,
            strike REAL,
            option_type TEXT,
            expiration_date TEXT,
            source_year INTEGER,
            PRIMARY KEY (trade_date, ticker)
        )
    """)

    today = date(2026, 5, 27)
    # 30 pregões de spot para PETR4
    base_close = 44.0
    spot_rows = []
    for i in range(30):
        d = today - timedelta(days=(30 - i))
        close = base_close + i * 0.1
        spot_rows.append((
            d.strftime("%Y-%m-%d"), "PETR4", "010",
            None, "PETROBRAS", None, None,
            close - 0.5, close + 0.5, close - 0.8, close, close,
            close - 0.05, close + 0.05,
            1000, 10000, close * 10000,
            None, None, None, 2026,
        ))

    # 10 pregões de CALL (070)
    exp_call = (today + timedelta(days=20)).strftime("%Y-%m-%d")  # DTE=20 → CURTO
    call_rows = []
    for i in range(10):
        d = today - timedelta(days=(10 - i))
        call_rows.append((
            d.strftime("%Y-%m-%d"), "PETRF440", "070",
            None, "PETROBRAS CALL", None, None,
            1.5, 2.0, 1.3, 1.7, 1.7,
            1.6, 1.8,
            50, 5000, 50 * 1700,     # volume=85_000 → liquidez alta
            44.0, "CALL", exp_call, 2026,
        ))

    # 10 pregões de PUT (080)
    exp_put = (today + timedelta(days=45)).strftime("%Y-%m-%d")  # DTE=45 → MEDIO
    put_rows = []
    for i in range(10):
        d = today - timedelta(days=(10 - i))
        put_rows.append((
            d.strftime("%Y-%m-%d"), "PETRR402", "080",
            None, "PETROBRAS PUT", None, None,
            0.8, 1.2, 0.7, 1.0, 1.0,
            0.9, 1.1,
            30, 3000, 30 * 1000,     # volume=30_000
            42.0, "PUT", exp_put, 2026,
        ))

    # 1 registro de termo (020) — DEVE SER EXCLUÍDO
    termo_row = (
        today.strftime("%Y-%m-%d"), "PETR4T", "020",
        None, "PETROBRAS TERMO", None, "30",
        44.0, 44.0, 44.0, 44.0, 44.0,
        43.9, 44.1,
        5, 500, 22000,
        None, None, None, 2026,
    )

    cols = """(trade_date, ticker, market_type, bdi_code, company_name,
               specification, term_days, open, high, low, average, close,
               best_bid, best_ask, trades, quantity, volume,
               strike, option_type, expiration_date, source_year)"""
    placeholders = "(" + ",".join(["?"] * 21) + ")"

    cur.executemany(f"INSERT OR IGNORE INTO cotahist_daily {cols} VALUES {placeholders}", spot_rows)
    cur.executemany(f"INSERT OR IGNORE INTO cotahist_daily {cols} VALUES {placeholders}", call_rows)
    cur.executemany(f"INSERT OR IGNORE INTO cotahist_daily {cols} VALUES {placeholders}", put_rows)
    cur.execute(f"INSERT OR IGNORE INTO cotahist_daily {cols} VALUES {placeholders}", termo_row)

    con.commit()
    con.close()


class TestRunComMock:
    @pytest.fixture
    def banco_mock(self, tmp_path) -> Path:
        db_path = tmp_path / "scanner_quant.db"
        _criar_banco_mock(db_path)
        return db_path

    def test_retorna_dataframe_nao_vazio(self, banco_mock, tmp_path):
        df = run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_colunas_esperadas_presentes(self, banco_mock, tmp_path):
        df = run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        colunas_esperadas = [
            "ativo_objeto", "ticker_opcao", "tipo", "strike", "vencimento",
            "dte", "categoria_vencimento", "ultimo_preco", "liquidez_score",
            "cenario", "score", "status", "moneyness_cat",
        ]
        for col in colunas_esperadas:
            assert col in df.columns, f"Coluna ausente: {col}"

    def test_filtra_market_type_corretamente(self, banco_mock, tmp_path):
        """Deve conter apenas CALL (070) e PUT (080), nunca TERMO (020)."""
        df = run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        tipos = df["tipo"].unique().tolist()
        assert set(tipos).issubset({"CALL", "PUT"})

    def test_exclui_market_type_020(self, banco_mock, tmp_path):
        """Ticker PETR4T (market_type=020) nunca deve aparecer."""
        df = run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        assert "PETR4T" not in df["ticker_opcao"].values

    def test_call_identificado_corretamente(self, banco_mock, tmp_path):
        df = run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        calls = df[df["ticker_opcao"] == "PETRF440"]
        assert len(calls) == 1
        assert calls.iloc[0]["tipo"] == "CALL"

    def test_put_identificado_corretamente(self, banco_mock, tmp_path):
        df = run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        puts = df[df["ticker_opcao"] == "PETRR402"]
        assert len(puts) == 1
        assert puts.iloc[0]["tipo"] == "PUT"

    def test_dte_calculado_corretamente(self, banco_mock, tmp_path):
        today_ref = date(2026, 5, 27)
        df = run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=today_ref,
        )
        # PETRF440 vence em today + 20 dias
        call_row = df[df["ticker_opcao"] == "PETRF440"].iloc[0]
        assert call_row["dte"] == 20, f"DTE esperado=20, obtido={call_row['dte']}"

        # PETRR402 vence em today + 45 dias
        put_row = df[df["ticker_opcao"] == "PETRR402"].iloc[0]
        assert put_row["dte"] == 45, f"DTE esperado=45, obtido={put_row['dte']}"

    def test_status_descartar_iliquida_para_liquidez_baixa(self, tmp_path):
        """Opção com volume=0 e trades=0 deve ter status DESCARTAR_ILIQUIDA."""
        db_path = tmp_path / "iliquida.db"
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE cotahist_daily (
                trade_date TEXT, ticker TEXT, market_type TEXT, bdi_code TEXT,
                company_name TEXT, specification TEXT, term_days TEXT,
                open REAL, high REAL, low REAL, average REAL, close REAL,
                best_bid REAL, best_ask REAL, trades INTEGER, quantity REAL,
                volume REAL, strike REAL, option_type TEXT, expiration_date TEXT,
                source_year INTEGER, PRIMARY KEY (trade_date, ticker)
            )
        """)
        today_ref = date(2026, 5, 27)
        # Spot PETR4
        for i in range(30):
            d = (today_ref - timedelta(days=30 - i)).strftime("%Y-%m-%d")
            cur.execute(
                "INSERT OR IGNORE INTO cotahist_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (d, "PETR4", "010", None, None, None, None,
                 44.0, 44.5, 43.5, 44.0, 44.0, 43.9, 44.1,
                 100, 1000, 44000, None, None, None, 2026),
            )
        # Opção CALL com volume=0, trades=0
        exp = (today_ref + timedelta(days=15)).strftime("%Y-%m-%d")
        cur.execute(
            "INSERT OR IGNORE INTO cotahist_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (today_ref.strftime("%Y-%m-%d"), "PETRF450", "070", None, None, None, None,
             0.5, 0.6, 0.4, 0.5, 0.5, 0.4, 0.6,
             0, 0, 0.0, 45.0, "CALL", exp, 2026),  # volume=0, trades=0
        )
        con.commit()
        con.close()

        df = run_historical_scanner(
            db_path=db_path,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=today_ref,
        )
        iliquida = df[df["ticker_opcao"] == "PETRF450"]
        assert len(iliquida) == 1
        assert iliquida.iloc[0]["status"] == StatusOportunidade.DESCARTAR_ILIQUIDA.value


# ─────────────────────────────────────────────────────────────────────────────
# 9. test_output_csv_cols
# ─────────────────────────────────────────────────────────────────────────────


class TestOutputCsvCols:
    @pytest.fixture
    def banco_mock(self, tmp_path) -> Path:
        db_path = tmp_path / "scanner_quant.db"
        _criar_banco_mock(db_path)
        return db_path

    def test_watchlist_csv_tem_colunas_corretas(self, banco_mock, tmp_path):
        run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        watchlist_path = tmp_path / "options_next_session_watchlist.csv"
        assert watchlist_path.exists(), "CSV watchlist não foi criado"

        df_watch = pd.read_csv(watchlist_path)
        for col in WATCHLIST_COLS:
            assert col in df_watch.columns, f"Coluna ausente no watchlist CSV: {col}"

    def test_oportunidades_csv_criado(self, banco_mock, tmp_path):
        run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        opp_path = tmp_path / "options_historical_opportunities.csv"
        assert opp_path.exists(), "CSV de oportunidades não foi criado"
        df_opp = pd.read_csv(opp_path)
        assert len(df_opp) > 0

    def test_watchlist_contém_apenas_candidatas_e_rtd(self, banco_mock, tmp_path):
        run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        watchlist_path = tmp_path / "options_next_session_watchlist.csv"
        df_watch = pd.read_csv(watchlist_path)

        if not df_watch.empty:
            statuses_validos = {
                StatusOportunidade.CANDIDATA_PROXIMO_PREGAO.value,
                StatusOportunidade.MONITORAR_NO_RTD.value,
            }
            assert set(df_watch["status"].unique()).issubset(statuses_validos)

    def test_oportunidades_csv_ordenado_por_score_desc(self, banco_mock, tmp_path):
        run_historical_scanner(
            db_path=banco_mock,
            ativos=["PETR4"],
            output_dir=tmp_path,
            today=date(2026, 5, 27),
        )
        df_opp = pd.read_csv(tmp_path / "options_historical_opportunities.csv")
        if len(df_opp) > 1:
            scores = df_opp["score"].tolist()
            assert scores == sorted(scores, reverse=True), "CSV não está ordenado por score DESC"


# ─────────────────────────────────────────────────────────────────────────────
# 10. test_estruturas_por_cenario
# ─────────────────────────────────────────────────────────────────────────────


class TestEstruturasPorCenario:
    def test_todos_os_cenarios_mapeados(self):
        for cenario in CenarioHistorico:
            assert cenario in ESTRUTURAS_POR_CENARIO, f"Cenário não mapeado: {cenario}"

    def test_recuperacao_sugere_calls(self):
        estruturas = ESTRUTURAS_POR_CENARIO[CenarioHistorico.RECUPERACAO_APOS_QUEDA]
        assert any("Call" in e for e in estruturas)

    def test_continuacao_alta_sugere_trava(self):
        estruturas = ESTRUTURAS_POR_CENARIO[CenarioHistorico.CONTINUACAO_ALTA]
        assert any("Alta" in e for e in estruturas)

    def test_continuacao_baixa_sugere_puts(self):
        estruturas = ESTRUTURAS_POR_CENARIO[CenarioHistorico.CONTINUACAO_BAIXA]
        assert any("Put" in e or "Baixa" in e for e in estruturas)

    def test_protecao_carteira_sugere_put(self):
        estruturas = ESTRUTURAS_POR_CENARIO[CenarioHistorico.PROTECAO_CARTEIRA]
        assert any("Put" in e or "Collar" in e for e in estruturas)

    def test_renda_sugere_covered_call(self):
        estruturas = ESTRUTURAS_POR_CENARIO[CenarioHistorico.RENDA_COM_ATIVO]
        assert any("Covered Call" in e for e in estruturas)

    def test_sem_assimetria_lista_vazia(self):
        estruturas = ESTRUTURAS_POR_CENARIO[CenarioHistorico.SEM_ASSIMETRIA]
        assert estruturas == []

    def test_volatilidade_em_alta_sugere_monitorar(self):
        estruturas = ESTRUTURAS_POR_CENARIO[CenarioHistorico.VOLATILIDADE_EM_ALTA]
        assert any("Monitorar" in e for e in estruturas)

    def test_lateralidade_sugere_iron_condor_futuro(self):
        estruturas = ESTRUTURAS_POR_CENARIO[CenarioHistorico.LATERALIDADE]
        assert any("Iron Condor" in e for e in estruturas)

    def test_estruturas_sao_listas(self):
        for cenario, estruturas in ESTRUTURAS_POR_CENARIO.items():
            assert isinstance(estruturas, list), f"Estruturas de {cenario} não é lista"

    def test_quantidade_cenarios(self):
        """Deve haver exatamente 8 cenários mapeados."""
        assert len(ESTRUTURAS_POR_CENARIO) == len(CenarioHistorico)
