"""Tests for the provider-neutral execution instrument contract."""

from execution_instrument_contract_v0_1 import (
    ExecutionInstrumentSpecification,
    InstrumentResolutionReason,
    InstrumentResolutionStatus,
    resolve_provider_instrument,
    validate_execution_instrument,
)


def spec(
    *,
    asset="BTC",
    settlement_asset="USDT",
    instrument_type=None,
):
    return ExecutionInstrumentSpecification(
        asset=asset,
        venue="FUTURES",
        settlement_asset=settlement_asset,
        instrument_type=instrument_type,
        selection_source="EXECUTION_POLICY",
        policy_version="v0.1",
    )


def candidate(symbol, *, asset="BTC", settlement="USDT", status="TRADING", instrument_type="PERPETUAL"):
    return {
        "asset": asset,
        "venue": "FUTURES",
        "settlement_asset": settlement,
        "instrument_type": instrument_type,
        "provider_symbol": symbol,
        "status": status,
    }


def test_unique_provider_contract_resolves():
    result = resolve_provider_instrument(
        spec(),
        [
            candidate("BTC-SWAP-USDT"),
            candidate("BTC-SWAP-USDC", settlement="USDC"),
        ],
    )

    assert result.status == InstrumentResolutionStatus.RESOLVED
    assert result.reason == InstrumentResolutionReason.RESOLVED
    assert result.provider_symbol == "BTC-SWAP-USDT"


def test_multiple_matching_contracts_fail_closed():
    result = resolve_provider_instrument(
        spec(),
        [
            candidate("BTC-SWAP-USDT-A"),
            candidate("BTC-SWAP-USDT-B"),
        ],
    )

    assert result.status == InstrumentResolutionStatus.BLOCK
    assert result.reason == InstrumentResolutionReason.AMBIGUOUS
    assert result.provider_symbol is None


def test_zero_matching_contracts_fail_closed():
    result = resolve_provider_instrument(
        spec(),
        [
            candidate("BTC-SWAP-USDC", settlement="USDC"),
        ],
    )

    assert result.status == InstrumentResolutionStatus.BLOCK
    assert result.reason == InstrumentResolutionReason.NOT_FOUND


def test_non_trading_contract_does_not_resolve():
    result = resolve_provider_instrument(
        spec(),
        [
            candidate("BTC-SWAP-USDT", status="OPEN_FORBIDDEN"),
        ],
    )

    assert result.status == InstrumentResolutionStatus.BLOCK
    assert result.reason == InstrumentResolutionReason.NOT_FOUND


def test_multiple_assets_are_not_cross_selected():
    result = resolve_provider_instrument(
        spec(asset="ETH"),
        [
            candidate("BTC-SWAP-USDT"),
            candidate("ETH-SWAP-USDT", asset="ETH"),
        ],
    )

    assert result.status == InstrumentResolutionStatus.RESOLVED
    assert result.provider_symbol == "ETH-SWAP-USDT"


def test_instrument_type_can_narrow_without_provider_symbol_in_core():
    result = resolve_provider_instrument(
        spec(instrument_type="PERPETUAL"),
        [
            candidate("BTC-SWAP-USDT", instrument_type="PERPETUAL"),
            candidate(
                "BTC-DELIVERY-USDT",
                instrument_type="DELIVERY",
            ),
        ],
    )

    assert result.status == InstrumentResolutionStatus.RESOLVED
    assert result.provider_symbol == "BTC-SWAP-USDT"


def test_forbidden_source_is_rejected():
    invalid = ExecutionInstrumentSpecification(
        asset="BTC",
        venue="FUTURES",
        settlement_asset="USDT",
        instrument_type="PERPETUAL",
        selection_source="TEST",
        policy_version="v0.1",
    )

    valid, reason = validate_execution_instrument(invalid)

    assert valid is False
    assert reason == "EXECUTION_INSTRUMENT_SOURCE_INVALID"


def test_futures_requires_settlement_asset():
    invalid = spec(settlement_asset=None)

    valid, reason = validate_execution_instrument(invalid)

    assert valid is False
    assert reason == "EXECUTION_INSTRUMENT_SETTLEMENT_ASSET_REQUIRED"
