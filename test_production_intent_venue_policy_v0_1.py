from types import SimpleNamespace

import pytest

from production_intent_venue_policy_v0_1 import (
    INSTRUMENT_SOURCE,
    POLICY_SOURCE,
    produce_authoritative_venue_evidence,
    select_venue_for_intent,
)


@pytest.mark.parametrize(("direction", "venue"), [("LONG", "SPOT"), ("SHORT", "FUTURES")])
def test_directional_policy_selects_explicit_venue(direction, venue):
    evidence = select_venue_for_intent(
        asset="BTC/USDT",
        direction=direction,
        intent_id="intent-123",
        observed_at="2026-10-11T12:00:00Z",
    )
    assert evidence["source"] == POLICY_SOURCE
    assert evidence["decision"] == "SELECTED"
    assert evidence["venue"] == venue
    assert evidence["intent_id"] == "intent-123"
    assert evidence["policy_version"]


def test_unknown_direction_fails_closed():
    with pytest.raises(ValueError, match="DIRECTION_UNSUPPORTED"):
        select_venue_for_intent(
            asset="BTC/USDT",
            direction="SELL",
            intent_id="intent-123",
            observed_at="2026-10-11T12:00:00Z",
        )


class _Adapter:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def trading_constraints(self, asset):
        self.calls.append(("SPOT", asset))
        return SimpleNamespace(allowed=True, reason="OK", data=self.row)

    def futures_trading_constraints(self, asset):
        self.calls.append(("FUTURES", asset))
        return SimpleNamespace(allowed=True, reason="OK", data=self.row)


def test_long_produces_selection_and_fresh_provider_instrument_evidence():
    adapter = _Adapter({"symbol": "BTCUSDT", "status": "TRADING"})
    selection, instrument = produce_authoritative_venue_evidence(
        request=SimpleNamespace(asset="BTC/USDT", direction="LONG", intent_id="i-1"),
        adapter=adapter,
        observed_at="2026-10-11T12:00:00Z",
    )
    assert adapter.calls == [("SPOT", "BTC/USDT")]
    assert selection["venue"] == "SPOT"
    assert instrument["source"] == INSTRUMENT_SOURCE
    assert instrument["instrument_id"] == "BTCUSDT"
    assert instrument["instrument_status"] == "TRADING"
    assert instrument["observed_at"] == selection["observed_at"]


def test_short_uses_futures_constraints():
    adapter = _Adapter({"symbol": "BTCUSDT", "status": "TRADING"})
    selection, instrument = produce_authoritative_venue_evidence(
        request=SimpleNamespace(asset="BTC/USDT", direction="SHORT", intent_id="i-2"),
        adapter=adapter,
        observed_at="2026-10-11T12:00:00Z",
    )
    assert adapter.calls == [("FUTURES", "BTC/USDT")]
    assert selection["venue"] == "FUTURES"
    assert instrument["venue"] == "FUTURES"


@pytest.mark.parametrize("row", [
    {"symbol": "BTCUSDT", "status": "HALT"},
    {"status": "TRADING"},
])
def test_invalid_or_non_trading_provider_instrument_blocks(row):
    adapter = _Adapter(row)
    with pytest.raises(RuntimeError):
        produce_authoritative_venue_evidence(
            request=SimpleNamespace(asset="BTC/USDT", direction="LONG", intent_id="i-3"),
            adapter=adapter,
            observed_at="2026-10-11T12:00:00Z",
        )


def test_provider_read_failure_blocks():
    class BrokenAdapter:
        def trading_constraints(self, asset):
            return SimpleNamespace(allowed=False, reason="NETWORK_ERROR", data=None)

    with pytest.raises(RuntimeError, match="INSTRUMENT_READ_FAILED"):
        produce_authoritative_venue_evidence(
            request=SimpleNamespace(asset="BTC/USDT", direction="LONG", intent_id="i-4"),
            adapter=BrokenAdapter(),
            observed_at="2026-10-11T12:00:00Z",
        )
