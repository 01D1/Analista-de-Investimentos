"""Tests para M023 — Backend services payloads (Watchlist, Quant, Signal Matrix, Thesis, Conviction, Agent Runtime).

Testa:
  - Cada service retorna dict (não exception)
  - Cada payload tem updated_at / timestamp
  - Cada endpoint retorna HTTP 200 com JSON válido
  - Campos principais existem
  - Empty state honesto quando aplicável
  - Nenhum mock enganoso

Roda:
  pytest tests/test_backend_services_payloads.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Import da app FastAPI
import sys
from pathlib import Path

# Garante que src/ está no path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from backend.main import app

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def assert_payload_structure(payload: dict, required_fields: list[str]) -> None:
    """Verifica que todos os campos obrigatórios existem no payload."""
    for field in required_fields:
        assert field in payload, f"Campo obrigatório ausente: {field}"


def assert_valid_timestamp(payload: dict, field: str = "timestamp") -> None:
    """Verifica que timestamp existe e é string ISO."""
    ts = payload.get(field)
    assert ts is not None, f"Campo '{field}' ausente"
    assert isinstance(ts, str), f"'{field}' deve ser string, got {type(ts)}"
    assert "T" in ts, f"'{field}' deve ser ISO datetime: {ts}"


def assert_no_html(payload: dict | list) -> None:
    """Verifica que não há HTML no payload."""
    import json
    text = json.dumps(payload).lower()
    assert "<html" not in text, "Payload contém HTML"
    assert "<div>" not in text, "Payload contém tags HTML"
    assert "<body>" not in text, "Payload contém tags HTML"


# ── M023: Watchlist ─────────────────────────────────────────────────────────

class TestWatchlistService:
    """Tests para /api/watchlist e watchlist_service."""

    def test_endpoint_returns_200(self):
        resp = client.get("/api/watchlist")
        assert resp.status_code == 200

    def test_returns_valid_json(self, resp=client.get("/api/watchlist")):
        data = resp.json()
        assert isinstance(data, dict)
        assert_no_html(data)

    def test_payload_has_required_fields(self):
        data = client.get("/api/watchlist").json()
        required = ["status", "timestamp", "tickers", "total", "diagnostic"]
        assert_payload_structure(data, required)

    def test_timestamp_present(self):
        data = client.get("/api/watchlist").json()
        assert_valid_timestamp(data)

    def test_tickers_is_list(self):
        data = client.get("/api/watchlist").json()
        assert isinstance(data["tickers"], list)

    def test_ticker_fields_present(self):
        data = client.get("/api/watchlist").json()
        for ticker in data["tickers"][:3]:  # Check first 3
            assert "ticker" in ticker
            assert "score" in ticker
            assert "direction" in ticker
            assert "status" in ticker
            assert "updated_at" in ticker or "source" in ticker

    def test_diagnostic_has_source(self):
        data = client.get("/api/watchlist").json()
        assert "source" in data["diagnostic"]
        assert data["diagnostic"]["source"] in (
            "asset_intelligence_snapshots",
            "realtime_signals",
            "unavailable",
        )

    def test_total_matches_tickers(self):
        data = client.get("/api/watchlist").json()
        assert data["total"] == len(data["tickers"])


# ── M023: Quant Signals ─────────────────────────────────────────────────────

class TestQuantSignalsService:
    """Tests para /api/quant/signals e quant_signals_service."""

    def test_endpoint_returns_200(self):
        resp = client.get("/api/quant/signals")
        assert resp.status_code == 200

    def test_returns_valid_json(self):
        data = client.get("/api/quant/signals").json()
        assert isinstance(data, dict)
        assert_no_html(data)

    def test_payload_has_required_fields(self):
        data = client.get("/api/quant/signals").json()
        required = ["status", "timestamp", "ranking", "total", "diagnostic"]
        assert_payload_structure(data, required)

    def test_timestamp_present(self):
        data = client.get("/api/quant/signals").json()
        assert_valid_timestamp(data)

    def test_ranking_is_list(self):
        data = client.get("/api/quant/signals").json()
        assert isinstance(data["ranking"], list)

    def test_ranking_fields_present(self):
        data = client.get("/api/quant/signals").json()
        for item in data["ranking"][:3]:
            assert "ticker" in item
            assert "score_final" in item
            assert "direction" in item

    def test_direction_values_valid(self):
        data = client.get("/api/quant/signals").json()
        valid_directions = {"BUY", "SELL", "WATCH", "HOLD"}
        for item in data["ranking"]:
            assert item["direction"] in valid_directions, \
                f"Direção inválida: {item['direction']}"

    def test_counts_match_ranking(self):
        data = client.get("/api/quant/signals").json()
        assert "counts" in data
        counts = data["counts"]
        total = sum(counts.values())
        assert total == len(data["ranking"])


# ── M023: Signal Matrix ─────────────────────────────────────────────────────

class TestSignalMatrixService:
    """Tests para /api/ai/signal-matrix e signal_matrix_service."""

    def test_endpoint_returns_200(self):
        resp = client.get("/api/ai/signal-matrix")
        assert resp.status_code == 200

    def test_returns_valid_json(self):
        data = client.get("/api/ai/signal-matrix").json()
        assert isinstance(data, dict)
        assert_no_html(data)

    def test_payload_has_required_fields(self):
        data = client.get("/api/ai/signal-matrix").json()
        required = ["status", "timestamp", "assets", "total"]
        assert_payload_structure(data, required)

    def test_timestamp_present(self):
        data = client.get("/api/ai/signal-matrix").json()
        assert_valid_timestamp(data)

    def test_assets_is_list(self):
        data = client.get("/api/ai/signal-matrix").json()
        assert isinstance(data["assets"], list)

    def test_asset_has_7_blocks(self):
        data = client.get("/api/ai/signal-matrix").json()
        core_blocks = {"tecnico", "momentum", "liquidez", "macro",
                       "opcoes", "valuation", "risco"}
        for asset in data["assets"][:3]:
            assert "blocos" in asset
            assert "score_agregado" in asset
            assert "conclusao" in asset
            actual_blocks = set(asset["blocos"].keys())
            # deve conter pelo menos os 7 blocos core (tecnico_indicadores é bônus)
            assert core_blocks.issubset(actual_blocks), \
                f"Core blocks missing: {core_blocks - actual_blocks}"

    def test_block_has_status(self):
        data = client.get("/api/ai/signal-matrix").json()
        valid_statuses = {"disponível", "disponivel", "em integração", "em integracao"}
        for asset in data["assets"][:2]:
            for block_name, block in asset["blocos"].items():
                assert "status" in block, f"Block {block_name} missing status"
                assert block["status"] in valid_statuses, \
                    f"Block {block_name} has invalid status: {block['status']}"

    def test_limit_param_respected(self):
        data = client.get("/api/ai/signal-matrix?limit=5").json()
        assert data["total"] <= 5

    def test_ticker_filter_works(self):
        resp = client.get("/api/ai/signal-matrix?ticker=PETR4")
        assert resp.status_code == 200
        data = resp.json()
        if data["assets"]:
            assert data["assets"][0]["ticker"] == "PETR4"


# ── M023: Thesis Builder ─────────────────────────────────────────────────────

class TestThesisService:
    """Tests para /api/ai/thesis e thesis_service."""

    def test_endpoint_returns_200(self):
        resp = client.get("/api/ai/thesis")
        assert resp.status_code == 200

    def test_returns_valid_json(self):
        data = client.get("/api/ai/thesis").json()
        assert isinstance(data, dict)
        assert_no_html(data)

    def test_payload_has_required_fields(self):
        data = client.get("/api/ai/thesis").json()
        required = ["status", "timestamp", "theses", "total"]
        assert_payload_structure(data, required)

    def test_timestamp_present(self):
        data = client.get("/api/ai/thesis").json()
        assert_valid_timestamp(data)

    def test_theses_is_list(self):
        data = client.get("/api/ai/thesis").json()
        assert isinstance(data["theses"], list)

    def test_thesis_fields_present(self):
        data = client.get("/api/ai/thesis").json()
        for thesis in data["theses"][:3]:
            assert "ticker" in thesis
            assert "status" in thesis
            assert "evidencias_bullish" in thesis
            assert "evidencias_bearish" in thesis
            assert isinstance(thesis["evidencias_bullish"], list)
            assert isinstance(thesis["evidencias_bearish"], list)

    def test_ticker_filter_works(self):
        resp = client.get("/api/ai/thesis?ticker=PETR4")
        assert resp.status_code == 200
        data = resp.json()
        if data["theses"]:
            assert data["theses"][0]["ticker"] == "PETR4"

    def test_empty_state_is_honest(self):
        data = client.get("/api/ai/thesis?ticker=NONEXIST999").json()
        # Deve retornar empty state, não exception
        assert data["status"] in ("ok", "partial", "error")
        assert isinstance(data["theses"], list)

    def test_status_values_valid(self):
        data = client.get("/api/ai/thesis").json()
        valid_statuses = {"dados_parciais", "em integração", "sem dados"}
        for thesis in data["theses"]:
            assert thesis["status"] in valid_statuses, \
                f"Tese {thesis['ticker']} status inválido: {thesis['status']}"


# ── M023: Conviction Desk ──────────────────────────────────────────────────

class TestConvictionService:
    """Tests para /api/conviction/positions e conviction_service."""

    def test_endpoint_returns_200(self):
        resp = client.get("/api/conviction/positions")
        assert resp.status_code == 200

    def test_returns_valid_json(self):
        data = client.get("/api/conviction/positions").json()
        assert isinstance(data, dict)
        assert_no_html(data)

    def test_payload_has_required_fields(self):
        data = client.get("/api/conviction/positions").json()
        required = ["status", "timestamp", "positions", "total", "empty_state"]
        assert_payload_structure(data, required)

    def test_timestamp_present(self):
        data = client.get("/api/conviction/positions").json()
        assert_valid_timestamp(data)

    def test_positions_is_list(self):
        data = client.get("/api/conviction/positions").json()
        assert isinstance(data["positions"], list)

    def test_counts_present(self):
        data = client.get("/api/conviction/positions").json()
        assert "counts" in data
        counts = data["counts"]
        assert all(k in counts for k in ["forte", "moderada", "baixa"])

    def test_position_fields_present(self):
        data = client.get("/api/conviction/positions").json()
        for pos in data["positions"][:3]:
            assert "ticker" in pos
            assert "score" in pos
            assert "conviction_level" in pos
            assert "status" in pos
            assert "timestamp" in pos

    def test_conviction_levels_valid(self):
        data = client.get("/api/conviction/positions").json()
        valid_levels = {"forte", "moderada", "baixa"}
        for pos in data["positions"]:
            assert pos["conviction_level"] in valid_levels

    def test_note_is_honest(self):
        data = client.get("/api/conviction/positions").json()
        assert "note" in data
        note = data["note"]
        assert isinstance(note, str)
        assert len(note) > 10


# ── M023: Agent Runtime ─────────────────────────────────────────────────────

class TestAgentRuntimeService:
    """Tests para /api/agents/status e agent_runtime_service."""

    def test_endpoint_returns_200(self):
        resp = client.get("/api/agents/status")
        assert resp.status_code == 200

    def test_returns_valid_json(self):
        data = client.get("/api/agents/status").json()
        assert isinstance(data, dict)
        assert_no_html(data)

    def test_payload_has_required_fields(self):
        data = client.get("/api/agents/status").json()
        required = [
            "status", "timestamp", "backend_status",
            "services_status", "db_status", "rtd_files",
            "services_available", "endpoints", "total_endpoints",
        ]
        assert_payload_structure(data, required)

    def test_timestamp_present(self):
        data = client.get("/api/agents/status").json()
        assert_valid_timestamp(data)

    def test_services_status_is_list(self):
        data = client.get("/api/agents/status").json()
        assert isinstance(data["services_status"], list)

    def test_services_status_fields(self):
        data = client.get("/api/agents/status").json()
        for svc in data["services_status"]:
            assert "name" in svc
            assert "status" in svc
            assert svc["status"] in {"ok", "degraded", "error"}

    def test_db_status_has_ok(self):
        data = client.get("/api/agents/status").json()
        assert "ok" in data["db_status"]

    def test_rtd_files_is_list(self):
        data = client.get("/api/agents/status").json()
        assert isinstance(data["rtd_files"], list)

    def test_services_available_count(self):
        data = client.get("/api/agents/status").json()
        assert data["available_count"] >= 0
        assert data["available_count"] <= data["total_services"]

    def test_endpoints_listed(self):
        data = client.get("/api/agents/status").json()
        expected_paths = [
            "/api/watchlist",
            "/api/quant/signals",
            "/api/ai/signal-matrix",
            "/api/ai/thesis",
            "/api/conviction/positions",
            "/api/agents/status",
        ]
        for path in expected_paths:
            assert any(e["path"] == path for e in data["endpoints"]), \
                f"Endpoint {path} não listado"

    def test_new_services_are_available(self):
        data = client.get("/api/agents/status").json()
        new_services = [
            "watchlist", "quant_signals", "signal_matrix",
            "thesis", "conviction", "agent_runtime",
        ]
        available = [s["name"] for s in data["services_available"] if s["available"]]
        for svc in new_services:
            assert svc in available, f"Service {svc} não disponível"


# ── Existing endpoints não quebraram ─────────────────────────────────────────

class TestExistingEndpoints:
    """Verifica que endpoints existentes continuam funcionando."""

    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_trading_live(self):
        resp = client.get("/api/trading/live")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_options_strategies(self):
        resp = client.get("/api/options/strategies")
        assert resp.status_code == 200

    def test_macro_b3(self):
        resp = client.get("/api/macro/b3")
        assert resp.status_code == 200

    def test_calendar_economic(self):
        resp = client.get("/api/calendar/economic")
        assert resp.status_code == 200

    def test_valuation_summary(self):
        resp = client.get("/api/valuation/summary")
        assert resp.status_code == 200

    def test_system_health(self):
        resp = client.get("/api/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "services" in data

    def test_radar_opportunities(self):
        resp = client.get("/api/radar/opportunities")
        assert resp.status_code == 200

    def test_opportunities_legacy(self):
        resp = client.get("/api/opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
