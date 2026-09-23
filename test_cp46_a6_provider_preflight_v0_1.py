"""
CP46-A6
PROVIDER PREFLIGHT / DUPLICATE PROTECTION TESTS

NO NETWORK.
NO DATABASE.
NO EXCHANGE.
NO EXECUTION.
"""

from dataclasses import replace

from provider_preflight_v0_1 import (
    PreflightReason,
    PreflightStatus,
    ProviderAccountState,
    ProviderContractState,
    ProviderOrderPreflightRequest,
    ProviderOrderState,
    ProviderPortfolioState,
    ProviderPreflightEvidence,
    ProviderTimestampState,
    run_provider_preflight,
)


def valid_request(
    *,
    venue="SPOT",
    order_type="LIMIT",
    quantity_unit="BASE_ASSET",
):
    return ProviderOrderPreflightRequest(
        symbol="BTCUSDT",
        direction="LONG",
        order_type=order_type,
        quantity="1",
        quantity_unit=quantity_unit,
        intent_id="intent-001",
        timestamp_ms=1_000_000,
        venue=venue,
    )


def valid_evidence():
    return ProviderPreflightEvidence(
        contract=ProviderContractState(
            symbol_valid=True,
            contract_valid=True,
            min_quantity="0.001",
            max_quantity="100",
            quantity_step="0.001",
            min_notional="5",
            max_notional="1000000",
        ),
        account=ProviderAccountState(
            state_known=True,
            balance_sufficient=True,
            margin_state_known=True,
            leverage_state_known=True,
            position_conflict=False,
        ),
        orders=ProviderOrderState(
            state_known=True,
            open_order_client_ids=frozenset(),
            recent_order_client_ids=frozenset(),
        ),
        timestamp=ProviderTimestampState(
            state_known=True,
            exchange_timestamp_ms=1_000_001,
            max_drift_ms=5000,
        ),
        portfolio=ProviderPortfolioState(
            state_known=True,
            exposure_allowed=True,
        ),
    )


def assert_block(result, reason):
    assert result.status == PreflightStatus.BLOCK
    assert result.reason == reason


def test_valid_spot_limit_long_passes():
    result = run_provider_preflight(
        valid_request(),
        valid_evidence(),
    )

    assert result.status == PreflightStatus.PASS
    assert result.reason == PreflightReason.PASS


def test_futures_base_asset_requires_translation():
    result = run_provider_preflight(
        valid_request(
            venue="FUTURES",
            quantity_unit="BASE_ASSET",
        ),
        valid_evidence(),
    )

    assert_block(
        result,
        PreflightReason.BLOCK_QUANTITY_TRANSLATION_REQUIRED,
    )


def test_spot_market_buy_base_asset_requires_translation():
    result = run_provider_preflight(
        valid_request(
            venue="SPOT",
            order_type="MARKET",
            quantity_unit="BASE_ASSET",
        ),
        valid_evidence(),
    )

    assert_block(
        result,
        PreflightReason.BLOCK_QUANTITY_TRANSLATION_REQUIRED,
    )


def test_duplicate_recent_intent_blocks():
    evidence = valid_evidence()

    evidence = replace(
        evidence,
        orders=ProviderOrderState(
            state_known=True,
            open_order_client_ids=frozenset(),
            recent_order_client_ids=frozenset(
                {"intent-001"}
            ),
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_DUPLICATE_ORDER,
    )


def test_open_order_conflict_blocks():
    evidence = valid_evidence()

    evidence = replace(
        evidence,
        orders=ProviderOrderState(
            state_known=True,
            open_order_client_ids=frozenset(
                {"intent-001"}
            ),
            recent_order_client_ids=frozenset(),
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_OPEN_ORDER_CONFLICT,
    )


def test_unknown_order_state_blocks():
    evidence = valid_evidence()

    evidence = replace(
        evidence,
        orders=ProviderOrderState(
            state_known=False,
            open_order_client_ids=frozenset(),
            recent_order_client_ids=frozenset(),
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_PROVIDER_STATE_INCONSISTENT,
    )


def test_position_conflict_blocks():
    evidence = valid_evidence()

    evidence = replace(
        evidence,
        account=ProviderAccountState(
            state_known=True,
            balance_sufficient=True,
            margin_state_known=True,
            leverage_state_known=True,
            position_conflict=True,
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_POSITION_CONFLICT,
    )


def test_unknown_margin_state_blocks():
    evidence = valid_evidence()

    evidence = replace(
        evidence,
        account=ProviderAccountState(
            state_known=True,
            balance_sufficient=True,
            margin_state_known=False,
            leverage_state_known=True,
            position_conflict=False,
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_MARGIN_STATE_UNKNOWN,
    )


def test_unknown_leverage_state_blocks():
    evidence = valid_evidence()

    evidence = replace(
        evidence,
        account=ProviderAccountState(
            state_known=True,
            balance_sufficient=True,
            margin_state_known=True,
            leverage_state_known=False,
            position_conflict=False,
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_LEVERAGE_STATE_UNKNOWN,
    )


def test_timestamp_drift_blocks():
    evidence = replace(
        valid_evidence(),
        timestamp=ProviderTimestampState(
            state_known=True,
            exchange_timestamp_ms=2_000_000,
            max_drift_ms=5000,
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_TIMESTAMP_DRIFT,
    )


def test_unknown_contract_state_blocks():
    evidence = replace(
        valid_evidence(),
        contract=ProviderContractState(
            symbol_valid=None,
            contract_valid=True,
            min_quantity="0.001",
            max_quantity="100",
            quantity_step="0.001",
            min_notional="5",
            max_notional="1000000",
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_SYMBOL_NOT_SUPPORTED,
    )


def test_quantity_below_minimum_blocks():
    request = replace(
        valid_request(),
        quantity="0.0001",
    )

    result = run_provider_preflight(
        request,
        valid_evidence(),
    )

    assert_block(
        result,
        PreflightReason.BLOCK_MIN_QUANTITY,
    )


def test_quantity_above_maximum_blocks():
    request = replace(
        valid_request(),
        quantity="101",
    )

    result = run_provider_preflight(
        request,
        valid_evidence(),
    )

    assert_block(
        result,
        PreflightReason.BLOCK_MAX_QUANTITY,
    )


def test_quantity_step_violation_blocks():
    request = replace(
        valid_request(),
        quantity="1.0005",
    )

    result = run_provider_preflight(
        request,
        valid_evidence(),
    )

    assert_block(
        result,
        PreflightReason.BLOCK_PRECISION_INVALID,
    )


def test_insufficient_balance_blocks():
    evidence = replace(
        valid_evidence(),
        account=ProviderAccountState(
            state_known=True,
            balance_sufficient=False,
            margin_state_known=True,
            leverage_state_known=True,
            position_conflict=False,
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_BALANCE_INSUFFICIENT,
    )


def test_portfolio_exposure_blocks():
    evidence = replace(
        valid_evidence(),
        portfolio=ProviderPortfolioState(
            state_known=True,
            exposure_allowed=False,
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_PORTFOLIO_EXPOSURE,
    )


def test_unknown_portfolio_state_blocks():
    evidence = replace(
        valid_evidence(),
        portfolio=ProviderPortfolioState(
            state_known=False,
            exposure_allowed=None,
        ),
    )

    result = run_provider_preflight(
        valid_request(),
        evidence,
    )

    assert_block(
        result,
        PreflightReason.BLOCK_PORTFOLIO_EXPOSURE,
    )


def test_invalid_direction_blocks():
    request = replace(
        valid_request(),
        direction="SELL",
    )

    result = run_provider_preflight(
        request,
        valid_evidence(),
    )

    assert_block(
        result,
        PreflightReason.BLOCK_DIRECTION_INVALID,
    )


def test_no_request_mutation():
    request = valid_request()
    evidence = valid_evidence()

    before = request

    result = run_provider_preflight(
        request,
        evidence,
    )

    assert result.status == PreflightStatus.PASS
    assert request == before
    assert request.quantity == "1"
    assert request.quantity_unit == "BASE_ASSET"


def test_no_quantity_conversion_for_futures():
    request = valid_request(
        venue="FUTURES",
        quantity_unit="BASE_ASSET",
    )

    original_quantity = request.quantity

    result = run_provider_preflight(
        request,
        valid_evidence(),
    )

    assert_block(
        result,
        PreflightReason.BLOCK_QUANTITY_TRANSLATION_REQUIRED,
    )

    assert request.quantity == original_quantity
    assert request.quantity_unit == "BASE_ASSET"