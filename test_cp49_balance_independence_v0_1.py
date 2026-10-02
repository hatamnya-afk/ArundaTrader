"""CP49 — capital-independent provider preflight regression tests."""

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


def _evidence() -> ProviderPreflightEvidence:
    return ProviderPreflightEvidence(
        contract=ProviderContractState(
            symbol_valid=True,
            contract_valid=True,
            min_quantity="1",
            max_quantity="100000",
            quantity_step="1",
            min_notional="1",
            max_notional="100000000",
        ),
        account=ProviderAccountState(
            state_known=True,
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
            exchange_timestamp_ms=1000,
            max_drift_ms=5000,
        ),
        portfolio=None,
    )


def _request() -> ProviderOrderPreflightRequest:
    return ProviderOrderPreflightRequest(
        symbol="BTCUSDT",
        direction="LONG",
        order_type="MARKET",
        quantity="10",
        quantity_unit="QUOTE_ASSET",
        intent_id="intent-1",
        timestamp_ms=1000,
        venue="SPOT",
    )


def test_account_balance_is_not_a_preflight_permission():
    result = run_provider_preflight(_request(), _evidence())

    assert result.status is PreflightStatus.PASS
    assert result.reason is PreflightReason.PASS


def test_account_state_contract_contains_no_synthetic_balance_permission():
    account = ProviderAccountState(
        state_known=True,
        margin_state_known=True,
        leverage_state_known=True,
        position_conflict=False,
    )

    assert not hasattr(account, "balance_sufficient")
