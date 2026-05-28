"""
tests/test_market_data_core.py — M029 Market Data Core Tests
============================================================

Testes para os 8 endpoints de market data core (ações, opções, futuros, histórico).
Verifica: 200 OK, presença de status/timestamp/source/diagnostic,
separação calls/puts, empty states honestos.
"""

from __future__ import annotations

import pytest


BASE = "http://127.0.0.1:8000"


def _get(path: str):
    """ helper: GET + status """
    import urllib.request, json
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as r:
            return r.status, json.loads(r.read())
    except Exception:
        # Try in-process test via direct import
        raise


# ── Market History ─────────────────────────────────────────────────────────

def test_asset_history_petr4():
    status, body = _get("/api/market/assets/PETR4/history")
    assert status == 200, f"Expected 200, got {status}"
    assert body["status"] == "ok", body.get("status")
    assert body["ticker"] == "PETR4"
    assert "ohlcv" in body
    assert "summary" in body
    assert "source" in body
    assert "timestamp" in body
    assert "diagnostic" in body
    # OHLCV snapshot fields
    ohlcv = body.get("ohlcv") or {}
    assert "close" in ohlcv or "open" in ohlcv or ohlcv == {}
    # Summary fields
    s = body.get("summary") or {}
    assert "last_close" in s
    assert "rsi" in s or s == {}


def test_asset_history_vale3():
    status, body = _get("/api/market/assets/VALE3/history")
    assert status == 200
    assert body["status"] == "ok"
    assert body["ticker"] == "VALE3"


def test_asset_history_unknown():
    status, body = _get("/api/market/assets/XYZ999/history")
    assert status == 200
    assert body["status"] in ("error", "ok")


def test_history_summary():
    status, body = _get("/api/market/assets/history-summary?tickers=PETR4,VALE3,WEGE3")
    assert status == 200
    assert body["status"] in ("ok", "partial")
    assert "tickers" in body
    assert "total" in body
    assert "timestamp" in body
    assert "diagnostic" in body
    assert body["total"] >= 0


def test_history_summary_one():
    status, body = _get("/api/market/assets/history-summary?tickers=PETR4")
    assert status == 200
    assert isinstance(body["tickers"], list)


def test_all_actions():
    status, body = _get("/api/market/actions")
    assert status == 200
    assert body["status"] == "ok"
    assert "actions" in body
    assert "total" in body
    assert body["total"] >= 0
    assert "timestamp" in body
    assert "diagnostic" in body
    if body["total"] > 0:
        a = body["actions"][0]
        assert "ticker" in a
        assert a.get("ticker") is not None


# ── Options Chain ─────────────────────────────────────────────────────────

def test_options_chain_petr():
    status, body = _get("/api/options/chain/PETR")
    assert status == 200
    assert body["status"] in ("ok", "empty")
    assert "underlying" in body
    assert body["underlying"] == "PETR"
    assert "calls" in body
    assert "puts" in body
    assert "calls_count" in body
    assert "puts_count" in body
    assert "source" in body
    assert "timestamp" in body
    assert "diagnostic" in body
    # Verify calls and puts are separated
    for c in body.get("calls", []):
        assert c.get("option_type") in ("CALL", None)
    for p in body.get("puts", []):
        assert p.get("option_type") in ("PUT", None)
    # Verify total = len(calls) + len(puts)
    assert len(body.get("calls", [])) + len(body.get("puts", [])) == body.get("total_options", 0) or body.get("total_options", 0) == 0


def test_options_chain_vale():
    status, body = _get("/api/options/chain/VALE")
    assert status == 200
    assert body["underlying"] == "VALE"


def test_options_chain_with_expiration():
    status, body = _get("/api/options/chain/PETR?expiration=2026-06-19")
    assert status == 200
    # Should filter to this expiration if any data exists
    assert "calls" in body and "puts" in body


def test_options_chain_unknown():
    status, body = _get("/api/options/chain/XYZ999")
    assert status == 200
    # Should return empty array, not crash
    assert "calls" in body and "puts" in body
    # Empty state honesto
    if body["total_options"] == 0:
        assert body["status"] == "empty"


# ── Options Radar ─────────────────────────────────────────────────────────

def test_options_radar():
    status, body = _get("/api/options/radar")
    assert status == 200
    assert body["status"] == "ok"
    assert "total" in body
    assert "by_status" in body
    assert "by_underlying" in body or body["total"] == 0
    assert "candidates_next_session" in body
    assert "monitor_rtd" in body
    assert "source" in body
    assert "timestamp" in body
    assert "diagnostic" in body


def test_options_radar_underlying_filter():
    status, body = _get("/api/options/radar?underlying=PETR4")
    assert status == 200
    assert body["status"] == "ok"
    if body["total"] > 0:
        # All options should be for PETR
        pass  # Just verify no crash


# ── Options History ────────────────────────────────────────────────────────

def test_option_history_valid():
    """ENEVR245 exists in options CSVs."""
    status, body = _get("/api/options/history/ENEVR245")
    assert status == 200
    assert body["status"] in ("ok", "error")
    if body["status"] == "ok":
        assert "ticker" in body
        assert "underlying" in body
        assert "option_type" in body
        assert "records" in body
        assert "summary" in body
        assert "record_count" in body["summary"]
        assert body["summary"]["record_count"] >= 0
        assert "source" in body
        assert "timestamp" in body


def test_option_history_unknown():
    status, body = _get("/api/options/history/XYZ999ZZZZ")
    assert status == 200
    # Should return empty/error, not crash


# ── Futures ───────────────────────────────────────────────────────────────

def test_futures_live():
    status, body = _get("/api/futures/live")
    assert status == 200
    assert body["status"] in ("ok", "error")
    assert "futures" in body
    assert "indices" in body
    assert "total" in body
    assert "futures_count" in body
    assert "indices_count" in body
    assert "source" in body
    assert "timestamp" in body
    assert "diagnostic" in body
    # Empty state honesto se nao ha futuros
    if body.get("total", 0) == 0:
        assert body["status"] == "ok"  # empty state is OK


def test_futures_summary():
    status, body = _get("/api/futures/summary")
    assert status == 200
    assert body["status"] in ("ok", "error")
    assert "futures" in body
    assert "indices" in body
    assert "summary" in body
    if body.get("total", 0) > 0:
        s = body["summary"]
        assert "by_ticker" in s or "ao_vivo" in s


# ── Diagnostic fields on all responses ──────────────────────────────────

def test_diagnostic_fields_present():
    """Every endpoint response must have status, timestamp, source, diagnostic."""
    endpoints = [
        "/api/market/assets/PETR4/history",
        "/api/market/assets/history-summary?tickers=PETR4",
        "/api/market/actions",
        "/api/options/chain/PETR",
        "/api/options/radar",
        "/api/options/history/ENEVR245",
        "/api/futures/live",
        "/api/futures/summary",
    ]
    for ep in endpoints:
        status, body = _get(ep)
        assert status == 200, f"{ep} returned {status}"
        assert "status" in body, f"{ep} missing 'status'"
        assert "timestamp" in body, f"{ep} missing 'timestamp'"
        assert "source" in body, f"{ep} missing 'source'"
        assert "diagnostic" in body, f"{ep} missing 'diagnostic'"


# ── Empty / null safety ─────────────────────────────────────────────────

def test_empty_ticker_list():
    """history-summary with empty tickers should not crash."""
    status, body = _get("/api/market/assets/history-summary?tickers=")
    assert status == 200
    assert body["total"] == 0
    assert body["tickers"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
