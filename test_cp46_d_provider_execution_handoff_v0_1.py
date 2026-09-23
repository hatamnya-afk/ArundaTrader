"""
CP46-D — PROVIDER EXECUTION HANDOFF TESTS

NO NETWORK.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO EXECUTION.
"""

from provider_order_translation_v0_1 import (
    ProviderOrderRequest,
    ProviderTranslationResult,
    ProviderTranslationEvidence,
    TranslationStatus,
    TranslationReason,
    translate_order_request,
)

from provider_preflight_v0_1 import (
    ProviderPreflightEvidence,
    ProviderContractState,
    ProviderAccountState,
    ProviderOrderState,
    ProviderTimestampState,
    ProviderPortfolioState,
    PreflightStatus,
    PreflightReason,
)

from exchange_execution_contract import (
    CanonicalOrderRequest,
)

from cp46_d_provider_execution_handoff_v0_1 import (
    HandoffStatus,
    build_preflight_request,
    handoff_to_provider_preflight,
)


def build_canonical_spot_limit() -> CanonicalOrderRequest:
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="LIMIT",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=None,
        intent_id="CP46-D-TEST-001",
        snapshot_id="CP46-D-SNAPSHOT-001",
        timestamp="1700000000000",
    )


def build_translation() -> ProviderTranslationResult:
    canonical = build_canonical_spot_limit()

    evidence = ProviderTranslationEvidence(
        provider_symbol="BTCUSDT",
    )

    return translate_order_request(
        canonical,
        evidence,
        venue="SPOT",
    )


def build_pass_evidence() -> ProviderPreflightEvidence:
    return ProviderPreflightEvidence(
        contract=ProviderContractState(
            symbol_valid=True,
            contract_valid=True,
            min_quantity=0.001,
            max_quantity=1000,
            quantity_step=0.001,
            min_notional=5,
            max_notional=1000000,
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
            exchange_timestamp_ms=1700000000000,
            max_drift_ms=5000,
        ),
        portfolio=ProviderPortfolioState(
            state_known=True,
            exposure_allowed=True,
        ),
    )


def test_translation_passes_before_handoff():
    result = build_translation()

    assert result.status == TranslationStatus.PASS
    assert isinstance(
        result.request,
        ProviderOrderRequest,
    )


def test_build_preflight_request_preserves_provider_quantity():
    translation = build_translation()
    provider_request = translation.request

    assert provider_request is not None

    original_quantity = provider_request.quantity

    preflight_request = build_preflight_request(
        provider_request
    )

    assert preflight_request is not None
    assert preflight_request.quantity == original_quantity
    assert preflight_request.quantity_unit == "BASE_ASSET"
    assert preflight_request.symbol == "BTCUSDT"
    assert preflight_request.venue == "SPOT"


def test_handoff_passes_when_preflight_passes():
    translation = build_translation()

    result = handoff_to_provider_preflight(
        translation,
        build_pass_evidence(),
    )

    assert result.status == HandoffStatus.PASS
    assert result.preflight is not None
    assert result.preflight.status == PreflightStatus.PASS
    assert result.provider_request is not None
    assert result.provider_request.quantity == 1


def test_handoff_blocks_translation_failure():
    failed_translation = ProviderTranslationResult(
        status=TranslationStatus.BLOCK,
        reason=TranslationReason.UNSUPPORTED_ROUTE,
        message="SHORT cannot be translated to Spot.",
        request=None,
    )

    result = handoff_to_provider_preflight(
        failed_translation,
        build_pass_evidence(),
    )

    assert result.status == HandoffStatus.BLOCK
    assert result.reason == "TRANSLATION_BLOCKED"
    assert result.provider_request is None
    assert result.preflight is None


def test_handoff_blocks_missing_provider_request():
    broken_translation = ProviderTranslationResult(
        status=TranslationStatus.PASS,
        reason=TranslationReason.PASS,
        message="Invalid successful translation fixture.",
        request=None,
    )

    result = handoff_to_provider_preflight(
        broken_translation,
        build_pass_evidence(),
    )

    assert result.status == HandoffStatus.BLOCK
    assert result.reason == "PROVIDER_REQUEST_MISSING"


def test_handoff_blocks_invalid_evidence():
    translation = build_translation()

    result = handoff_to_provider_preflight(
        translation,
        None,
    )

    assert result.status == HandoffStatus.BLOCK
    assert result.reason == "PREFLIGHT_EVIDENCE_INVALID"


def test_handoff_preserves_quantity_after_preflight():
    translation = build_translation()
    provider_request = translation.request

    assert provider_request is not None

    original_quantity = provider_request.quantity

    result = handoff_to_provider_preflight(
        translation,
        build_pass_evidence(),
    )

    assert result.provider_request is provider_request
    assert provider_request.quantity == original_quantity
    assert result.preflight is not None


def test_timestamp_is_transferred_without_clock_access():
    translation = build_translation()

    provider_request = translation.request
    assert provider_request is not None

    preflight_request = build_preflight_request(
        provider_request
    )

    assert preflight_request is not None
    assert preflight_request.timestamp_ms == 1700000000000


def test_invalid_timestamp_blocks_before_preflight():
    provider_request = ProviderOrderRequest(
        venue="SPOT",
        symbol="BTCUSDT",
        side="BUY",
        position_side=None,
        order_type="LIMIT",
        quantity=1,
        quantity_unit="BASE_ASSET",
        entry_price=100,
        intent_id="CP46-D-TEST-BAD-TIME",
        snapshot_id="CP46-D-SNAPSHOT-BAD-TIME",
        timestamp="NOT-A-TIMESTAMP",
    )

    assert build_preflight_request(
        provider_request
    ) is None


def test_preflight_block_is_propagated():
    translation = build_translation()

    evidence = build_pass_evidence()

    blocked_evidence = ProviderPreflightEvidence(
        contract=evidence.contract,
        account=ProviderAccountState(
            state_known=True,
            balance_sufficient=False,
            margin_state_known=True,
            leverage_state_known=True,
            position_conflict=False,
        ),
        orders=evidence.orders,
        timestamp=evidence.timestamp,
        portfolio=evidence.portfolio,
    )

    result = handoff_to_provider_preflight(
        translation,
        blocked_evidence,
    )

    assert result.status == HandoffStatus.BLOCK
    assert result.reason == "PREFLIGHT_BLOCKED"
    assert result.preflight is not None
    assert (
        result.preflight.reason
        == PreflightReason.BLOCK_BALANCE_INSUFFICIENT
    )


def test_no_quantity_conversion_in_handoff():
    translation = build_translation()

    provider_request = translation.request
    assert provider_request is not None

    assert provider_request.quantity == 1
    assert provider_request.quantity_unit == "BASE_ASSET"

    result = handoff_to_provider_preflight(
        translation,
        build_pass_evidence(),
    )

    assert result.provider_request is provider_request
    assert result.provider_request.quantity == 1
    assert result.provider_request.quantity_unit == "BASE_ASSET"


def test_handoff_does_not_create_execution_result():
    translation = build_translation()

    result = handoff_to_provider_preflight(
        translation,
        build_pass_evidence(),
    )

    assert not hasattr(
        result,
        "exchange_order_id",
    )

    assert not hasattr(
        result,
        "executed_quantity",
    )

    assert not hasattr(
        result,
        "executed_price",
    )