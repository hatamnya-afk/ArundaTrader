"""Focused verification for zero-capital Trade Ready quantity observability."""

import arunda_pipeline


class _MarketResult:
    source = "REAL_MARKET"
    candles = ({"timestamp": 1_700_000_000_000},)


def test_zero_capital_trade_ready_quantity_is_preserved(monkeypatch):
    monkeypatch.setattr(
        arunda_pipeline.market_data_engine,
        "calculate_real_atr14",
        lambda candles: 100.0,
    )

    risk_snapshot = {
        "BTC": {
            "risk_state": "APPROVED",
            "risk_budget": 0.0,
            "position_size": 0.0,
            "entry_price": 100000.0,
            "stop_distance": 1000.0,
            "quantity_unit": "BASE_ASSET",
            "quantity_source": "POSITION_SIZING.position_size",
        }
    }

    records = arunda_pipeline.build_trade_ready_quantity_records(
        {"BTC"},
        risk_snapshot,
        {"BTC/USDT": _MarketResult()},
        {"BTC": {"snapshot_id": "REAL|BTC/USDT|1h|1700000000000"}},
    )

    row = records["BTC"]
    assert row["risk_budget"] == 0.0
    assert row["position_size"] == 0.0
    assert row["risk_position_quantity"] == 0.0
    assert row["order_intent_quantity"] is None
    assert row["canonical_order_request_quantity"] is None


def test_negative_zero_capital_values_still_fail(monkeypatch):
    monkeypatch.setattr(
        arunda_pipeline.market_data_engine,
        "calculate_real_atr14",
        lambda candles: 100.0,
    )

    risk_snapshot = {
        "BTC": {
            "risk_state": "APPROVED",
            "risk_budget": -0.01,
            "position_size": -0.01,
            "entry_price": 100000.0,
            "stop_distance": 1000.0,
            "quantity_unit": "BASE_ASSET",
            "quantity_source": "POSITION_SIZING.position_size",
        }
    }

    try:
        arunda_pipeline.build_trade_ready_quantity_records(
            {"BTC"},
            risk_snapshot,
            {"BTC/USDT": _MarketResult()},
            {"BTC": {"snapshot_id": "REAL|BTC/USDT|1h|1700000000000"}},
        )
    except RuntimeError as exc:
        assert "risk_budget invalid" in str(exc)
    else:
        raise AssertionError("negative risk budget was accepted")
