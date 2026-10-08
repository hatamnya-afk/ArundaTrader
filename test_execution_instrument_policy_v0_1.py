"""Tests for the explicit execution instrument policy producer."""

import pytest

from execution_instrument_policy_v0_1 import (
    FUTURES_INSTRUMENT_TYPE,
    FUTURES_SETTLEMENT_ASSET,
    POLICY_VERSION,
    SELECTION_SOURCE,
    build_execution_instrument_specification,
)


def test_futures_policy_produces_neutral_specification():
    spec = build_execution_instrument_specification(
        asset="btc",
        venue="futures",
    )

    assert spec.asset == "BTC"
    assert spec.venue == "FUTURES"
    assert spec.settlement_asset == FUTURES_SETTLEMENT_ASSET == "USDT"
    assert spec.instrument_type == FUTURES_INSTRUMENT_TYPE == "PERPETUAL"
    assert spec.selection_source == SELECTION_SOURCE
    assert spec.policy_version == POLICY_VERSION
    assert "TOOBIT" not in repr(spec).upper()
    assert "SWAP" not in repr(spec).upper()


def test_policy_applies_to_any_asset_without_symbol_reconstruction():
    for asset in ("BTC", "ETH", "SOL"):
        spec = build_execution_instrument_specification(
            asset=asset,
            venue="FUTURES",
        )
        assert spec.asset == asset
        assert spec.settlement_asset == "USDT"
        assert spec.instrument_type == "PERPETUAL"


def test_spot_has_no_futures_instrument_semantics():
    spec = build_execution_instrument_specification(
        asset="BTC",
        venue="SPOT",
    )

    assert spec.asset == "BTC"
    assert spec.venue == "SPOT"
    assert spec.settlement_asset is None
    assert spec.instrument_type is None


def test_invalid_asset_blocks():
    with pytest.raises(ValueError, match="EXECUTION_INSTRUMENT_ASSET_INVALID"):
        build_execution_instrument_specification(
            asset="",
            venue="FUTURES",
        )


def test_invalid_venue_blocks():
    with pytest.raises(ValueError, match="EXECUTION_INSTRUMENT_VENUE_INVALID"):
        build_execution_instrument_specification(
            asset="BTC",
            venue="OPTIONS",
        )
