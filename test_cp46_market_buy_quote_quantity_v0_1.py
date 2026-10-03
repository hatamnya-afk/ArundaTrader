"""
Focused regression contract for Toobit Spot MARKET BUY quantity semantics.

A MARKET BUY quantity is QUOTE_ASSET on Toobit. LOT_SIZE is base-asset
quantity metadata and must not be applied to the quote amount.
"""

from provider_preflight_v0_1 import (
    PreflightReason,
    PreflightStatus,
    ProviderAccountState,
    ProviderContractState,
    ProviderOrderPreflightRequest,
    ProviderOrderState,
    ProviderPreflightEvidence,
    ProviderTimestampState,
    run_provider_preflight,
)


def _evidence():
    return ProviderPreflightEvidence(
        contract=ProviderContractState(
            symbol_valid=True,
            contract_valid=True,
            min_quantity="0.0001",
            max_quantity="4000",
            quantity_step="0.0001",
            quote_min_amount="10",
            quote_max_amount="6600000",
            min_notional="10",
            max_notional="6600000",
        ),
        account=ProviderAccountState(
            state_known=True,
            margin_state_known=None,
            leverage_state_known=None,
            position_conflict=None,
        ),
        orders=ProviderOrderState(
            state_known=True,
            open_order_client_ids=frozenset(),
            recent_order_client_ids=frozenset(),
        ),
        timestamp=ProviderTimestampState(
            state_known=True,
            exchange_timestamp_ms=1700000000000,
            max_drift_ms=5000,
        ),
        portfolio=None,
    )


def _request(quantity, quantity_unit="QUOTE_ASSET"):
    return ProviderOrderPreflightRequest(
        symbol="ACHUSDT",
        direction="LONG",
        order_type="MARKET",
        quantity=quantity,
        quantity_unit=quantity_unit,
        intent_id="CP46-QTY-001",
        timestamp_ms=1700000000000,
        venue="SPOT",
    )


def test_market_buy_quote_quantity_does_not_use_base_lot_step():
    result = run_provider_preflight(
        _request("17.37"),
        _evidence(),
    )

    assert result.status == PreflightStatus.PASS
    assert result.reason == PreflightReason.PASS


def test_market_buy_quote_quantity_uses_trade_amount_bounds():
    below = run_provider_preflight(
        _request("9.99"),
        _evidence(),
    )
    above = run_provider_preflight(
        _request("6600000.01"),
        _evidence(),
    )

    assert below.status == PreflightStatus.BLOCK
    assert below.reason == PreflightReason.BLOCK_MIN_QUANTITY
    assert above.status == PreflightStatus.BLOCK
    assert above.reason == PreflightReason.BLOCK_MAX_QUANTITY


def test_spot_limit_base_quantity_still_uses_lot_step():
    request = ProviderOrderPreflightRequest(
        symbol="ACHUSDT",
        direction="LONG",
        order_type="LIMIT",
        quantity="1.00005",
        quantity_unit="BASE_ASSET",
        intent_id="CP46-QTY-002",
        timestamp_ms=1700000000000,
        venue="SPOT",
        reference_price="1",
    )

    result = run_provider_preflight(request, _evidence())

    assert result.status == PreflightStatus.BLOCK
    assert result.reason == PreflightReason.BLOCK_PRECISION_INVALID
