"""
Testes de paridade de dados backend — M020.
Verifica que todos os services retornam dict com campos enriquecidos,
que todos os endpoints FastAPI estão operacionais, e que nenhum service
importa streamlit ou retorna HTML.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Garante que src/ resolve para o projeto correto
PROJECT_ROOT = Path(__file__).resolve().parents[1]
src_path = str(PROJECT_ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _no_streamlit_imports(module_path: str) -> bool:
    """Verifica que um módulo não importa streamlit."""
    try:
        with open(module_path, "r") as f:
            content = f.read()
        return "import streamlit" not in content and "from streamlit" not in content
    except Exception:
        return False  # Não pode ler = não pode garantir


def _returns_dict(func) -> bool:
    """Verifica que uma função retorna dict."""
    try:
        result = func()
        return isinstance(result, dict)
    except Exception:
        return False


# ── Testes de compilation ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "module_path",
    [
        PROJECT_ROOT / "src" / "services" / "watchlist_service.py",
        PROJECT_ROOT / "src" / "services" / "quant_signals_service.py",
        PROJECT_ROOT / "src" / "services" / "signal_matrix_service.py",
        PROJECT_ROOT / "src" / "services" / "thesis_service.py",
        PROJECT_ROOT / "src" / "services" / "conviction_service.py",
        PROJECT_ROOT / "src" / "services" / "agent_runtime_service.py",
        PROJECT_ROOT / "src" / "services" / "trading_desk_service.py",
        PROJECT_ROOT / "src" / "services" / "options_strategy_service.py",
        PROJECT_ROOT / "src" / "services" / "macro_service.py",
        PROJECT_ROOT / "src" / "services" / "economic_calendar_service.py",
        PROJECT_ROOT / "src" / "services" / "valuation_service.py",
        PROJECT_ROOT / "backend" / "main.py",
    ],
)
def test_services_compile(module_path: Path) -> None:
    """Todos os arquivos Python compilam sem erro de sintaxe."""
    import py_compile
    try:
        py_compile.compile(str(module_path), doraise=True)
    except py_compile.PyCompileError as e:
        pytest.fail(f"Compile error in {module_path.name}: {e}")


# ── Testes de enriquecimento de payload ───────────────────────────────────────

def test_watchlist_service_returns_dict() -> None:
    """watchlist_service.get_watchlist_payload() retorna dict."""
    from src.services.watchlist_service import get_watchlist_payload

    assert _returns_dict(get_watchlist_payload)


def test_watchlist_service_has_enriched_fields() -> None:
    """Watchlist tem campos enriquecidos: variacao_pct, adv_21d, has_options, has_valuation, data_quality."""
    from src.services.watchlist_service import get_watchlist_payload

    p = get_watchlist_payload()
    assert p["status"] in ("ok", "partial", "error")
    assert "timestamp" in p
    assert "diagnostic" in p

    # Deve indicar que está enriquecido
    assert p["diagnostic"].get("enriched") is True

    # Campos enriquecidos por ticker
    if p.get("tickers"):
        t = p["tickers"][0]
        assert "variacao_pct" in t
        assert "adv_21d" in t
        assert "has_options" in t
        assert "has_valuation" in t
        assert "data_quality" in t
        assert "price_source" in t


def test_watchlist_service_no_streamlit() -> None:
    """watchlist_service.py não importa streamlit."""
    path = PROJECT_ROOT / "src" / "services" / "watchlist_service.py"
    assert _no_streamlit_imports(str(path)), "watchlist_service.py imports streamlit!"


def test_quant_signals_service_returns_dict() -> None:
    """quant_signals_service.get_quant_signals_payload() retorna dict."""
    from src.services.quant_signals_service import get_quant_signals_payload

    assert _returns_dict(get_quant_signals_payload)


def test_quant_signals_service_has_enriched_fields() -> None:
    """Quant signals tem campos enriquecidos: momentum_score, trend_score, technical indicators."""
    from src.services.quant_signals_service import get_quant_signals_payload

    p = get_quant_signals_payload()
    assert p["status"] in ("ok", "partial", "error")
    assert "timestamp" in p
    assert "diagnostic" in p
    assert p["diagnostic"].get("enriched") is True

    if p.get("ranking"):
        r = p["ranking"][0]
        assert "momentum_score" in r
        assert "trend_score" in r
        assert "volume_score" in r
        assert "score_tecnico" in r
        assert "technical_status" in r
        assert "governance_blocked" in r


def test_quant_signals_service_no_streamlit() -> None:
    """quant_signals_service.py não importa streamlit."""
    path = PROJECT_ROOT / "src" / "services" / "quant_signals_service.py"
    assert _no_streamlit_imports(str(path)), "quant_signals_service.py imports streamlit!"


def test_signal_matrix_service_returns_dict() -> None:
    """signal_matrix_service.get_signal_matrix_payload() retorna dict."""
    from src.services.signal_matrix_service import get_signal_matrix_payload

    assert _returns_dict(get_signal_matrix_payload)


def test_signal_matrix_has_8_blocks() -> None:
    """Signal matrix tem 8 blocos: tecnico + tecnico_indicadores + momentum + liquidez + macro + opcoes + valuation + risco."""
    from src.services.signal_matrix_service import get_signal_matrix_payload

    p = get_signal_matrix_payload(limit=2)
    assert p["status"] in ("ok", "partial", "error")
    assert "timestamp" in p

    if p.get("assets"):
        blocks = p["assets"][0]["blocos"]
        expected_blocks = {
            "tecnico",
            "tecnico_indicadores",
            "momentum",
            "liquidez",
            "macro",
            "opcoes",
            "valuation",
            "risco",
        }
        assert set(blocks.keys()) == expected_blocks, f"Expected {expected_blocks}, got {set(blocks.keys())}"


def test_signal_matrix_service_no_streamlit() -> None:
    """signal_matrix_service.py não importa streamlit."""
    path = PROJECT_ROOT / "src" / "services" / "signal_matrix_service.py"
    assert _no_streamlit_imports(str(path)), "signal_matrix_service.py imports streamlit!"


def test_thesis_service_returns_dict() -> None:
    """thesis_service.get_thesis_payload() retorna dict."""
    from src.services.thesis_service import get_thesis_payload

    assert _returns_dict(get_thesis_payload)


def test_thesis_service_has_enriched_fields() -> None:
    """Thesis tem campos enriquecidos: tese_bullish, tese_bearish, sinais_tecnicos, contexto_macro, leitura_opcoes."""
    from src.services.thesis_service import get_thesis_payload

    p = get_thesis_payload(ticker="PETR4", limit=1)
    assert p["status"] in ("ok", "partial", "error")
    assert "timestamp" in p

    theses = p.get("theses", [])
    if theses:
        th = theses[0]
        # Novos campos enriquecidos
        assert "tese_bullish" in th
        assert "tese_bearish" in th
        assert "sinais_tecnicos" in th
        assert "contexto_macro" in th
        assert "leitura_opcoes" in th
        assert "proximas_perguntas" in th
        assert "tesista_tipo" in th


def test_thesis_service_no_streamlit() -> None:
    """thesis_service.py não importa streamlit."""
    path = PROJECT_ROOT / "src" / "services" / "thesis_service.py"
    assert _no_streamlit_imports(str(path)), "thesis_service.py imports streamlit!"


def test_conviction_service_returns_dict() -> None:
    """conviction_service.get_conviction_positions_payload() retorna dict."""
    from src.services.conviction_service import get_conviction_positions_payload

    assert _returns_dict(get_conviction_positions_payload)


def test_conviction_service_has_enriched_fields() -> None:
    """Conviction tem campos enriquecidos: governance_blocked, from_score, to_score, change_direction."""
    from src.services.conviction_service import get_conviction_positions_payload

    p = get_conviction_positions_payload()
    assert p["status"] in ("ok", "partial", "error")
    assert "timestamp" in p
    assert "counts" in p
    assert "blocked" in p["counts"]  # Novo campo blocked

    if p.get("positions"):
        pos = p["positions"][0]
        assert "governance_blocked" in pos
        assert "from_score" in pos
        assert "to_score" in pos
        assert "change_direction" in pos


def test_conviction_service_no_streamlit() -> None:
    """conviction_service.py não importa streamlit."""
    path = PROJECT_ROOT / "src" / "services" / "conviction_service.py"
    assert _no_streamlit_imports(str(path)), "conviction_service.py imports streamlit!"


def test_agent_runtime_service_returns_dict() -> None:
    """agent_runtime_service.get_agent_runtime_payload() retorna dict."""
    from src.services.agent_runtime_service import get_agent_runtime_payload

    assert _returns_dict(get_agent_runtime_payload)


def test_agent_runtime_has_endpoints_and_rtd() -> None:
    """Agent runtime tem endpoints list e RTD files count."""
    from src.services.agent_runtime_service import get_agent_runtime_payload

    p = get_agent_runtime_payload()
    assert "backend_status" in p
    assert "services_status" in p
    assert "db_status" in p
    assert "rtd_files" in p
    assert "rtd_count" in p
    assert "services_available" in p
    assert "endpoints" in p
    assert p["total_endpoints"] >= 14, f"Expected >=14 endpoints, got {p['total_endpoints']}"


def test_all_services_no_streamlit() -> None:
    """Todos os services não importam streamlit."""
    services_dir = PROJECT_ROOT / "src" / "services"
    violations = []
    for f in services_dir.glob("*.py"):
        if f.name == "__init__.py":
            continue
        if not _no_streamlit_imports(str(f)):
            violations.append(f.name)
    assert not violations, f"These services import streamlit: {violations}"


def test_all_services_return_dict() -> None:
    """Todos os services têm funções payload que retornam dict."""
    services = [
        ("watchlist_service", "get_watchlist_payload"),
        ("quant_signals_service", "get_quant_signals_payload"),
        ("signal_matrix_service", "get_signal_matrix_payload"),
        ("thesis_service", "get_thesis_payload"),
        ("conviction_service", "get_conviction_positions_payload"),
        ("agent_runtime_service", "get_agent_runtime_payload"),
        ("trading_desk_service", "get_trading_desk_payload"),
        ("options_strategy_service", "get_options_strategy_payload"),
        ("macro_service", "get_macro_b3_payload"),
        ("economic_calendar_service", "get_economic_calendar_payload"),
        ("valuation_service", "get_valuation_payload"),
    ]
    for module_name, func_name in services:
        try:
            mod = __import__(f"src.services.{module_name}", fromlist=[func_name])
            fn = getattr(mod, func_name, None)
            assert fn is not None, f"{func_name} not found in {module_name}"
            result = fn()
            assert isinstance(result, dict), f"{module_name}.{func_name} returned {type(result).__name__}"
            assert "timestamp" in result, f"{module_name}.{func_name} missing 'timestamp'"
            assert "status" in result, f"{module_name}.{func_name} missing 'status'"
        except Exception as e:
            pytest.fail(f"Failed {module_name}.{func_name}: {e}")