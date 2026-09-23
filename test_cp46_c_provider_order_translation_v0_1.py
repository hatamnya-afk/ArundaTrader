from __future__ import annotations

from exchange_execution_contract import CanonicalOrderRequest
from provider_order_translation_v0_1 import (
    ProviderTranslationEvidence,
    TranslationReason,
    TranslationStatus,
    translate_order_request,
)


def canonical(
    *,
    direction="LONG",
    order_type="LIMIT",
    quantity=1,
    entry_price=100.0,
):
    return CanonicalOrderRequest(
        asset="BTC",
        direction=direction,
        order_type=order_type,
        quantity=quantity,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=entry_price,
        reference_price=100.0,
        intent_id="CP46-C-INTENT-001",
        snapshot_id="CP46-C-SNAPSHOT-001",
        timestamp="2026-09-23T00:00:00+00:00",
    )


def test_spot_limit_long_passes_without_quantity_mutation():
    request = canonical()

    result = translate_order_request(
        request,
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
        ),
        venue="SPOT",
    )

    assert result.status is TranslationStatus.PASS
    assert result.reason is TranslationReason.PASS

    assert result.request is not None
    assert result.request.venue == "SPOT"
    assert result.request.symbol == "BTCUSDT"
    assert result.request.side == "BUY"
    assert result.request.quantity == 1
    assert result.request.quantity_unit == "BASE_ASSET"

    assert request.quantity == 1


def test_spot_short_is_blocked():
    result = translate_order_request(
        canonical(direction="SHORT"),
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
        ),
        venue="SPOT",
    )

    assert result.status is TranslationStatus.BLOCK
    assert result.reason is TranslationReason.UNSUPPORTED_ROUTE
    assert result.request is None


def test_spot_market_buy_without_authoritative_quote_quantity_blocks():
    result = translate_order_request(
        canonical(
            order_type="MARKET",
            entry_price=None,
        ),
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
        ),
        venue="SPOT",
    )

    assert result.status is TranslationStatus.BLOCK
    assert (
        result.reason
        is TranslationReason.MARKET_BUY_QUOTE_QUANTITY_REQUIRED
    )


def test_spot_market_buy_with_authoritative_quote_quantity_passes():
    result = translate_order_request(
        canonical(
            order_type="MARKET",
            entry_price=None,
        ),
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
            quote_quantity=100.0,
        ),
        venue="SPOT",
    )

    assert result.status is TranslationStatus.PASS
    assert result.request is not None
    assert result.request.quantity == 100.0
    assert result.request.quantity_unit == "QUOTE_ASSET"


def test_futures_without_multiplier_blocks():
    result = translate_order_request(
        canonical(direction="SHORT"),
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
            contract_quantity_step=1,
        ),
        venue="FUTURES",
    )

    assert result.status is TranslationStatus.BLOCK
    assert (
        result.reason
        is TranslationReason.CONTRACT_MULTIPLIER_REQUIRED
    )


def test_futures_uses_authoritative_multiplier():
    request = canonical(direction="SHORT", quantity=1)

    result = translate_order_request(
        request,
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
            contract_multiplier=0.001,
            contract_quantity_step=1,
        ),
        venue="FUTURES",
    )

    assert result.status is TranslationStatus.PASS
    assert result.request is not None

    assert result.request.side == "SELL"
    assert result.request.position_side == "SHORT"
    assert result.request.quantity == 1000
    assert result.request.quantity_unit == "CONTRACTS"

    # Canonical request is unchanged.
    assert request.quantity == 1
    assert request.quantity_unit == "BASE_ASSET"


def test_futures_invalid_contract_step_blocks():
    result = translate_order_request(
        canonical(quantity=1),
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
            contract_multiplier=0.003,
            contract_quantity_step=1,
        ),
        venue="FUTURES",
    )

    assert result.status is TranslationStatus.BLOCK
    assert (
        result.reason
        is TranslationReason.CONTRACT_QUANTITY_PRECISION_INVALID
    )


def test_symbol_mapping_is_required():
    result = translate_order_request(
        canonical(),
        ProviderTranslationEvidence(
            provider_symbol=None,
        ),
        venue="SPOT",
    )

    assert result.status is TranslationStatus.BLOCK
    assert (
        result.reason
        is TranslationReason.SYMBOL_MAPPING_REQUIRED
    )


def test_invalid_venue_blocks():
    result = translate_order_request(
        canonical(),
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
        ),
        venue="UNKNOWN",
    )

    assert result.status is TranslationStatus.BLOCK
    assert result.reason is TranslationReason.UNSUPPORTED_ROUTE


def test_canonical_quantity_never_changes():
    request = canonical(quantity=7)

    result = translate_order_request(
        request,
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
            contract_multiplier=0.001,
            contract_quantity_step=1,
        ),
        venue="FUTURES",
    )

    assert result.status is TranslationStatus.PASS
    assert request.quantity == 7
    assert request.quantity_unit == "BASE_ASSET"
    assert request.quantity_source == "RISK.position_quantity"


def test_no_price_based_market_buy_conversion():
    request = canonical(
        order_type="MARKET",
        quantity=2,
        entry_price=None,
    )

    result = translate_order_request(
        request,
        ProviderTranslationEvidence(
            provider_symbol="BTCUSDT",
            quote_quantity=None,
        ),
        venue="SPOT",
    )

    assert result.status is TranslationStatus.BLOCK
    assert (
        result.reason
        is TranslationReason.MARKET_BUY_QUOTE_QUANTITY_REQUIRED
    )