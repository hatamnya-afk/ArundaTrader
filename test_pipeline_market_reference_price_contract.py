from types import SimpleNamespace

import pytest

from arunda_pipeline import resolve_authoritative_reference_price


def test_reference_price_uses_latest_real_candle_close():
    market = SimpleNamespace(
        source="TOOBIT_REAL_MARKET",
        candles=(
            {"timestamp": 1791593100, "close": 49900.0},
            {"timestamp": 1791596700, "close": 50125.5},
        ),
    )
    assert resolve_authoritative_reference_price(market) == 50125.5


def test_reference_price_prefers_explicit_current_provider_price():
    market = SimpleNamespace(
        last_price=50100.0,
        candles=({"timestamp": 1791596700, "close": 50000.0},),
    )
    assert resolve_authoritative_reference_price(market) == 50100.0


def test_reference_price_fails_closed_without_real_candle_or_explicit_price():
    market = SimpleNamespace(source="TOOBIT_REAL_MARKET", candles=())
    with pytest.raises(RuntimeError, match="no current real candles"):
        resolve_authoritative_reference_price(market)


def test_reference_price_rejects_invalid_latest_close_without_fallback():
    market = SimpleNamespace(
        source="TOOBIT_REAL_MARKET",
        candles=({"timestamp": 1791596700, "close": 0},),
    )
    with pytest.raises(RuntimeError, match="reference price unavailable"):
        resolve_authoritative_reference_price(market)
