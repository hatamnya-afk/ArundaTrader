from provider_order_translation_v0_1 import (
    ProviderTranslationEvidence,
    TranslationStatus,
    translate_order_request,
)
from exchange_execution_contract import CanonicalOrderRequest
from provider_preflight_v0_1 import (
    ProviderAccountState,
    ProviderContractState,
    ProviderOrderPreflightRequest,
    ProviderOrderState,
    ProviderPreflightEvidence,
    ProviderTimestampState,
    PreflightReason,
    PreflightStatus,
    run_provider_preflight,
)


def _canonical_request():
    return CanonicalOrderRequest(
        asset="APE",
        direction="LONG",
        order_type="LIMIT",
        quantity="1",
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price="1",
        reference_price=None,
        intent_id="OI-APE",
        snapshot_id="KUCOIN|APE/USDT|1h|1000",
        # Deliberately old Decision-Birth timestamp.
        timestamp="1000000000000",
        decision_id="DEC-APE",
    )


def _evidence():
    return ProviderPreflightEvidence(
        contract=ProviderContractState(
            symbol_valid=True,
            contract_valid=True,
            min_quantity="0.001",
            max_quantity="100000",
            quantity_step="0.001",
            min_notional="1",
            max_notional="1000000",
        ),
        account=ProviderAccountState(
            state_known=True,
            margin_state_known=None,
            leverage_state_known=None,
            position_conflict=False,
        ),
        orders=ProviderOrderState(
            state_known=True,
            open_order_client_ids=frozenset(),
            recent_order_client_ids=frozenset(),
        ),
        timestamp=ProviderTimestampState(
            state_known=True,
            exchange_timestamp_ms=2000000000000,
            max_drift_ms=5000,
        ),
        portfolio=None,
    )


def test_provider_timestamp_is_boundary_time_not_decision_birth_time():
    canonical = _canonical_request()

    result = translate_order_request(
        canonical,
        ProviderTranslationEvidence(
            provider_symbol="APEUSDT",
            provider_request_timestamp="2000000000000",
        ),
        venue="SPOT",
    )

    assert result.status is TranslationStatus.PASS
    assert result.request is not None

    # Canonical Decision-Birth identity/time is untouched.
    assert canonical.timestamp == "1000000000000"

    # Provider request receives authoritative provider-boundary time.
    assert result.request.timestamp == "2000000000000"


def test_old_decision_timestamp_does_not_fail_provider_preflight_when_boundary_time_is_fresh():
    canonical = _canonical_request()

    translated = translate_order_request(
        canonical,
        ProviderTranslationEvidence(
            provider_symbol="APEUSDT",
            provider_request_timestamp="2000000000000",
        ),
        venue="SPOT",
    )

    assert translated.status is TranslationStatus.PASS
    assert translated.request is not None

    request = translated.request
    preflight_request = ProviderOrderPreflightRequest(
        symbol=request.symbol,
        direction="LONG",
        order_type=request.order_type,
        quantity=request.quantity,
        quantity_unit=request.quantity_unit,
        intent_id=request.intent_id,
        timestamp_ms=2000000000000,
        venue=request.venue,
        reference_price=request.entry_price,
    )

    result = run_provider_preflight(
        preflight_request,
        _evidence(),
    )

    assert result.status is PreflightStatus.PASS
    assert result.reason is PreflightReason.PASS
