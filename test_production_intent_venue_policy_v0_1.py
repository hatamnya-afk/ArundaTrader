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
        self.execution_instrument = None

    def trading_constraints(self, asset):
        self.calls.append(("SPOT", asset))
        return SimpleNamespace(allowed=True, reason="OK", data=self.row)

    def futures_trading_constraints(self, asset, *, execution_instrument=None):
        self.calls.append(("FUTURES", asset))
        self.execution_instrument = execution_instrument
        return SimpleNamespace(allowed=True, reason="OK", data=self.row)


def test_long_produces_selection_and_fresh_provider_instrument_evidence():
    adapter = _Adapter({"symbol": "BTCUSDT", "status": "TRADING"})
    selection, instrument = produce_authoritative_venue_evidence(
        request=SimpleNamespace(asset="BTC/USDT", direction="LONG", intent_id="i-1"),
        adapter=adapter,
        observed_at="2026-10-11T12:00:00Z",
    )
    assert adapter.calls == [("SPOT", "BTC")]
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
    assert adapter.calls == [("FUTURES", "BTC")]
    assert adapter.execution_instrument.settlement_asset == "USDT"
    assert adapter.execution_instrument.instrument_type == "PERPETUAL"
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


def test_provider_evidence_timestamp_is_taken_after_metadata_read(monkeypatch):
    import production_intent_venue_policy_v0_1 as policy
    from datetime import datetime as RealDateTime, timezone

    class Clock:
        current = "2026-10-11T12:00:00+00:00"

        @staticmethod
        def fromisoformat(value):
            return RealDateTime.fromisoformat(value)

        @classmethod
        def now(cls, tz=None):
            return RealDateTime.fromisoformat(cls.current)

    class AdvancingAdapter(_Adapter):
        def trading_constraints(self, asset):
            result = super().trading_constraints(asset)
            Clock.current = "2026-10-11T12:00:03+00:00"
            return result

    monkeypatch.setattr(policy, "datetime", Clock)
    adapter = AdvancingAdapter({"symbol": "BTCUSDT", "status": "TRADING"})
    selection, instrument = policy.produce_authoritative_venue_evidence(
        request=SimpleNamespace(asset="BTC", direction="LONG", intent_id="i-clock"),
        adapter=adapter,
    )
    assert selection["observed_at"] == "2026-10-11T12:00:03+00:00"
    assert instrument["observed_at"] == selection["observed_at"]



@pytest.mark.parametrize(
    ("direction", "expected_symbol", "rows_key", "row"),
    [
        ("LONG", "BTCUSDT", "symbols", {
            "symbol": "BTCUSDT", "status": "TRADING",
            "baseAsset": "BTC", "quoteAsset": "USDT",
        }),
        ("SHORT", "BTC-SWAP-USDT", "contracts", [
            {
                "symbol": "BTC-SWAP", "status": "TRADING",
                "underlying": "BTC", "marginToken": "BTC",
                "inverse": True, "contractMultiplier": "1.0",
            },
            {
                "symbol": "BTC-SWAP-USDT", "status": "TRADING",
                "underlying": "BTC", "marginToken": "USDT",
                "inverse": False, "contractMultiplier": "0.0001",
            },
        ]),
    ],
)
def test_real_adapter_contract_resolves_base_asset_from_canonical_pair(
    direction, expected_symbol, rows_key, row
):
    from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter

    calls = []

    def transport(*, method, path, params, headers, base_url):
        calls.append((method, path))
        assert method == "GET"
        assert path == "/api/v1/exchangeInfo"
        rows = row if isinstance(row, list) else [row]
        return {
            "symbols": rows if rows_key == "symbols" else [],
            "contracts": rows if rows_key == "contracts" else [],
        }

    adapter = ToobitExchangeAdapter(transport=transport)
    selection, instrument = produce_authoritative_venue_evidence(
        request=SimpleNamespace(
            asset="BTC/USDT",
            direction=direction,
            intent_id="integration-intent",
        ),
        adapter=adapter,
    )

    expected_reads = 1 if direction == "LONG" else 2
    assert calls == [("GET", "/api/v1/exchangeInfo")] * expected_reads
    assert selection["venue"] == ("SPOT" if direction == "LONG" else "FUTURES")
    assert instrument["instrument_id"] == expected_symbol
    assert instrument["instrument_status"] == "TRADING"


def test_missing_intent_id_blocks_before_provider_read():
    adapter = _Adapter({"symbol": "BTCUSDT", "status": "TRADING"})
    with pytest.raises(ValueError, match="VENUE_POLICY_INTENT_ID_INVALID"):
        produce_authoritative_venue_evidence(
            request=SimpleNamespace(
                asset="BTC/USDT",
                direction="LONG",
                intent_id="",
            ),
            adapter=adapter,
        )
    assert adapter.calls == []
