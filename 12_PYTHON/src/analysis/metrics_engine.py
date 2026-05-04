"""
metrics_engine.py
-----------------
Calcula automaticamente todas as métricas financeiras a partir dos
dados processados em data/processed/{ticker}/.

Fluxo:
  1. Carregar dados processados via ProcessedStore
  2. Extrair campos por tipo (banco vs industrial)
  3. Alimentar calculate_bank_metrics / calculate_industrial_metrics
  4. Enriquecer com dados de mercado (preço atual via B3Scraper)
  5. Persistir em data/output/{ticker}/metrics.json

Uso:
    from src.analysis.metrics_engine import run_metrics

    result = run_metrics("BBAS3")          # todos os anos disponíveis
    result = run_metrics("BBAS3", years=[2022, 2023, 2024])
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)


def _ensure_src_path() -> None:
    src = str(Path(__file__).parent.parent)
    if src not in sys.path:
        sys.path.insert(0, src)


class MetricsEngine:
    """
    Calcula e persiste métricas para um ticker a partir dos dados processados.

    Args:
        output_dir: Raiz de data/output/ (default: via settings)
    """

    def __init__(self, output_dir: Path | None = None):
        from config.settings import settings

        self.output_dir = output_dir or settings.data_output

    def run(
        self,
        ticker: str,
        years: list[int] | None = None,
        force: bool = False,
    ) -> dict[int, dict]:
        """
        Calcula métricas para todos os anos disponíveis.

        Returns:
            {year: metrics_dict}
        """
        from src.processing.storage import ProcessedStore
        from src.valuation.sector_config import SectorConfig

        store = ProcessedStore()
        available = store.available_years(ticker)
        if not available:
            log.warning(f"[{ticker}] sem dados processados — execute 'process' primeiro")
            return {}

        target_years = years or available
        target_years = [y for y in target_years if y in available]

        cfg = SectorConfig.for_ticker(ticker)
        is_bank = cfg.is_bank_model

        # Carregar todos de uma vez para ter acesso a períodos anteriores
        all_data = store.load_all(ticker)
        latest_price = self._get_latest_price(ticker)

        results: dict[int, dict] = {}
        for year in sorted(target_years):
            # pass cfg into each period calculation
            output_path = self.output_dir / ticker / f"metrics_{year}.json"
            if output_path.exists() and not force:
                try:
                    results[year] = json.loads(output_path.read_text())
                    log.info(f"[{ticker}] {year}: métricas carregadas do cache")
                    continue
                except Exception:
                    pass

            data = all_data.get(year)
            prev_data = all_data.get(year - 1)
            if not data:
                log.warning(f"[{ticker}] {year}: dados não encontrados")
                continue

            try:
                if is_bank:
                    metrics = self._calc_bank(ticker, year, data, prev_data, latest_price)
                else:
                    metrics = self._calc_industrial(ticker, year, data, prev_data, latest_price)

                # Anotar setor para uso downstream
                metrics["sector_type"] = cfg.sector_type
                metrics["key_metrics"] = cfg.key_metrics

                self._save(metrics, output_path)
                results[year] = metrics
                log.info(f"[{ticker}] {year}: métricas calculadas [{cfg.sector_type}]")
            except Exception as exc:
                log.error(f"[{ticker}] {year}: erro ao calcular métricas — {exc}", exc_info=True)

        log.success(f"[{ticker}] {len(results)} períodos calculados")
        return results

    # ── Cálculo banco ─────────────────────────────────────────────────────────

    def _calc_bank(
        self,
        ticker: str,
        year: int,
        data: dict,
        prev_data: dict | None,
        price: float | None,
    ) -> dict:
        _ensure_src_path()
        from valuation.calculate_metrics import calculate_bank_metrics

        inc = data.get("income_statement") or {}
        bal = data.get("balance_sheet") or {}
        assets = (bal.get("assets") or {}) if isinstance(bal, dict) else {}
        liab = (bal.get("liabilities") or {}) if isinstance(bal, dict) else {}

        prev_inc = (prev_data.get("income_statement") or {}) if prev_data else {}
        prev_bal = (prev_data.get("balance_sheet") or {}) if prev_data else {}
        prev_assets = (prev_bal.get("assets") or {}) if isinstance(prev_bal, dict) else {}
        prev_liab = (prev_bal.get("liabilities") or {}) if isinstance(prev_bal, dict) else {}

        m = calculate_bank_metrics(
            ticker=ticker,
            year=year,
            total_revenues=_f(inc, "total_financial_revenues"),
            nii_gross=_f(inc, "nii_gross"),
            fee_income=_f(inc, "fee_income"),
            loan_loss_provision=_f(inc, "loan_loss_provision"),
            admin_expenses=_f(inc, "admin_expenses"),
            personnel_expenses=_f(inc, "personnel_expenses"),
            other_op_expenses=_f(inc, "other_operating_expenses"),
            ebt=_f(inc, "ebt"),
            net_income=_f(inc, "net_income"),
            total_assets=_f(assets, "total_assets"),
            shareholders_equity=_f(liab, "shareholders_equity"),
            loan_portfolio_gross=_f(assets, "loan_portfolio_gross"),
            prev_total_assets=_f(prev_assets, "total_assets") or None,
            prev_shareholders_equity=_f(prev_liab, "shareholders_equity") or None,
            prev_loan_portfolio=_f(prev_assets, "loan_portfolio_gross") or None,
            prev_net_income=_f(prev_inc, "net_income") or None,
            prev_nii=_f(prev_inc, "nii_gross") or None,
            price=price,
        )

        d = {k: v for k, v in m.__dict__.items() if v is not None}
        d["ticker"] = ticker
        d["year"] = year
        d["type"] = "bank"
        d["calculated_at"] = str(date.today())
        if price:
            d["market_price"] = price
        return d

    # ── Cálculo industrial ────────────────────────────────────────────────────

    def _calc_industrial(
        self,
        ticker: str,
        year: int,
        data: dict,
        prev_data: dict | None,
        price: float | None,
    ) -> dict:
        _ensure_src_path()
        from valuation.calculate_metrics import calculate_industrial_metrics

        # Para industrial, o dado é um dict de DataFrames serializados
        dre = self._extract_industrial_value(data, "DRE")
        bpa = self._extract_industrial_value(data, "BPA")
        bpp = self._extract_industrial_value(data, "BPP")
        dfc = self._extract_industrial_value(data, "DFC")

        self._extract_industrial_value(prev_data, "BPA") if prev_data else {}
        self._extract_industrial_value(prev_data, "BPP") if prev_data else {}
        prev_dre = self._extract_industrial_value(prev_data, "DRE") if prev_data else {}
        self._extract_industrial_value(prev_data, "DFC") if prev_data else {}

        net_revenue = _fk(dre, "net_revenue")
        gross_profit = _fk(dre, "gross_profit")
        ebit = _fk(dre, "ebit")
        net_income = _fk(dre, "net_income")
        cfo = _fk(dfc, "cfo")
        capex = _fk(dfc, "capex")
        da = _fk(dfc, "depreciation_amortization_cfo")
        ebitda = ebit + abs(da) if ebit and da else 0.0
        short_debt = _fk(bpp, "short_term_debt") or 0.0
        long_debt = _fk(bpp, "long_term_debt") or 0.0
        gross_debt = short_debt + long_debt
        cash = _fk(bpa, "cash") or 0.0

        m = calculate_industrial_metrics(
            ticker=ticker,
            year=year,
            net_revenue=net_revenue,
            gross_profit=gross_profit,
            ebit=ebit,
            ebitda=ebitda,
            net_income=net_income,
            total_assets=_fk(bpa, "total_current_assets")
            + (_fk(bpa, "total_non_current_assets") or 0.0),
            shareholders_equity=_fk(bpp, "total_equity")
            - (_fk(bpp, "minority_interest_bs") or 0.0),
            gross_debt=gross_debt,
            cash=cash,
            cfo=cfo,
            capex=capex,
            depreciation=da,
            prev_net_revenue=_fk(prev_dre, "net_revenue") or None,
            prev_ebitda=None,
            prev_net_income=_fk(prev_dre, "net_income") or None,
            price=price,
        )

        d = {k: v for k, v in m.__dict__.items() if v is not None}
        d["ticker"] = ticker
        d["year"] = year
        d["type"] = "industrial"
        d["calculated_at"] = str(date.today())
        if price:
            d["market_price"] = price
        return d

    @staticmethod
    def _extract_industrial_value(data: dict | None, stmt: str) -> dict:
        """Converte lista de registros em {normalized_name: value}."""
        if not data:
            return {}
        records = data.get(stmt, [])
        result: dict[str, float] = {}
        for row in records:
            name = row.get("normalized_name")
            val = row.get("value")
            if name and val is not None and name not in result:
                try:
                    result[name] = float(val)
                except (TypeError, ValueError):
                    pass
        return result

    # ── Preço de mercado ──────────────────────────────────────────────────────

    @staticmethod
    def _get_latest_price(ticker: str) -> float | None:
        try:
            from src.ingestion.b3_scraper import B3Scraper

            df = B3Scraper().load(ticker)
            if not df.empty:
                return float(df["close"].iloc[-1])
        except Exception:
            pass
        return None

    # ── Persistência ─────────────────────────────────────────────────────────

    @staticmethod
    def _save(data: dict, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))


# ── Helpers ───────────────────────────────────────────────────────────────────


def _f(d: dict, key: str) -> float:
    """Extrai float de dict, retorna 0.0 se ausente/None."""
    val = d.get(key)
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _fk(d: dict, key: str) -> float:
    return _f(d, key)


# ── Função de alto nível ──────────────────────────────────────────────────────


def run_metrics(
    ticker: str,
    years: list[int] | None = None,
    force: bool = False,
) -> dict[int, dict]:
    """Calcula e persiste métricas para um ticker."""
    return MetricsEngine().run(ticker, years=years, force=force)
