import pandas as pd

from src.options.options_chain_normalizer import infer_option_type, normalize_options_chain, validate_options_chain


def test_infer_option_type_from_b3_ticker():
    assert infer_option_type("PETRA123") == "CALL"
    assert infer_option_type("PETRM123") == "PUT"
    assert infer_option_type("XYZ") == "UNKNOWN"


def test_normalize_options_chain_basic():
    raw = pd.DataFrame(
        [
            {
                "trade_date": "2026-05-01",
                "ticker": "PETRA100",
                "underlying": "PETR4",
                "option_type": "CALL",
                "strike": 30,
                "expiration_date": "2026-06-01",
                "close": 1.2,
                "best_bid": 1.1,
                "best_ask": 1.3,
                "volume": 10000,
                "trades": 20,
                "underlying_price": 31,
            }
        ]
    )

    chain = normalize_options_chain(raw)
    valid, report = validate_options_chain(chain)

    assert chain.loc[0, "option_ticker"] == "PETRA100"
    assert chain.loc[0, "spread_pct"] > 0
    assert valid.shape[0] == 1
    assert "STRIKE_AUSENTE" in report["issue"].tolist()


def test_validate_options_chain_rejects_bid_above_ask():
    chain = normalize_options_chain(
        pd.DataFrame(
            [
                {
                    "trade_date": "2026-05-01",
                    "ticker": "PETRA100",
                    "underlying": "PETR4",
                    "option_type": "CALL",
                    "strike": 30,
                    "expiration_date": "2026-06-01",
                    "close": 1.2,
                    "best_bid": 1.4,
                    "best_ask": 1.3,
                    "volume": 10000,
                }
            ]
        )
    )
    valid, report = validate_options_chain(chain)

    assert valid.empty
    assert report.loc[report["issue"] == "BID_MAIOR_ASK", "count"].iloc[0] == 1
