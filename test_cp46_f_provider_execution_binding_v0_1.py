"""Focused CP46-F provider execution binding tests."""

from __future__ import annotations

from cp46_d_provider_execution_handoff_v0_1 import (
    ProviderExecutionHandoffResult,
    HandoffStatus,
)
from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from provider_order_translation_v0_1 import ProviderOrderRequest
from cp46_f_provider_execution_binding_v0_1 import (
    BindingStatus,
    build_provider_execution_binding,
)
from exchange_execution_contract import CanonicalOrderRequest


def _canonical():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="I-1",
        snapshot_id="S-1",
        timestamp="2026-09-23T00:00:00+00:00",
    )


def _provider():
    return ProviderOrderRequest(
        venue="SPOT",
        symbol="BTCUSDT",
        side="BUY",
        position_side=None,
        order_type="MARKET",
        quantity=100,
        quantity_unit="QUOTE_ASSET",
        entry_price=None,
        intent_id="I-1",
        snapshot_id="S-1",
        timestamp="2026-09-23T00:00:00+00:00",
    )


def _eligibility(canonical):
    return ExecutionEligibilityResult(
        status=EligibilityStatus.PASS,
        reason="PASS",
        message="PASS",
        canonical_request=canonical,
    )


def _handoff(provider):
    class Preflight:
        status = "PASS"

    return ProviderExecutionHandoffResult(
        status=HandoffStatus.PASS,
        reason="PASS",
        message="PASS",
        provider_request=provider,
        preflight=Preflight(),
    )


def test_requires_eligibility():
    result = build_provider_execution_binding(None, _handoff(_provider()))
    assert result.status == BindingStatus.BLOCK


def test_requires_eligibility_pass():
    canonical = _canonical()
    eligibility = ExecutionEligibilityResult(
        status=EligibilityStatus.BLOCK,
        reason="BLOCK",
        message="BLOCK",
        canonical_request=canonical,
    )
    result = build_provider_execution_binding(eligibility, _handoff(_provider()))
    assert result.status == BindingStatus.BLOCK


def test_requires_handoff_pass():
    canonical = _canonical()
    handoff = ProviderExecutionHandoffResult(
        status=HandoffStatus.BLOCK,
        reason="BLOCK",
        message="BLOCK",
        provider_request=_provider(),
        preflight=None,
    )
    result = build_provider_execution_binding(_eligibility(canonical), handoff)
    assert result.status == BindingStatus.BLOCK


def test_requires_preflight_pass():
    canonical = _canonical()
    handoff = ProviderExecutionHandoffResult(
        status=HandoffStatus.PASS,
        reason="PASS",
        message="PASS",
        provider_request=_provider(),
        preflight=None,
    )
    result = build_provider_execution_binding(_eligibility(canonical), handoff)
    assert result.status == BindingStatus.BLOCK


def test_identity_mismatch_blocks():
    canonical = _canonical()
    provider = _provider()
    provider = ProviderOrderRequest(
        **{**provider.__dict__, "intent_id": "I-2"}
    )
    result = build_provider_execution_binding(
        _eligibility(canonical),
        _handoff(provider),
    )
    assert result.reason == "INTENT_ID_MISMATCH"


def test_timestamp_mismatch_blocks():
    canonical = _canonical()
    provider = _provider()
    provider = ProviderOrderRequest(
        **{**provider.__dict__, "timestamp": "2026-09-23T00:01:00+00:00"}
    )
    result = build_provider_execution_binding(
        _eligibility(canonical),
        _handoff(provider),
    )
    assert result.reason == "TIMESTAMP_MISMATCH"


def test_spot_long_passes_and_preserves_objects():
    canonical = _canonical()
    provider = _provider()
    result = build_provider_execution_binding(
        _eligibility(canonical),
        _handoff(provider),
    )
    assert result.status == BindingStatus.PASS
    assert result.canonical_request is canonical
    assert result.provider_request is provider
    assert result.provider_request.quantity == 100
    assert result.provider_request.quantity_unit == "QUOTE_ASSET"


def test_spot_short_blocks():
    canonical = CanonicalOrderRequest(
        asset="BTC",
        direction="SHORT",
        quantity_unit="BASE_ASSET",
        order_type="MARKET",
        quantity=1,
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="I-1",
        snapshot_id="S-1",
        timestamp="2026-09-23T00:00:00+00:00",
    )
    result = build_provider_execution_binding(
        _eligibility(canonical),
        _handoff(_provider()),
    )
    assert result.reason == "SPOT_DIRECTION_MISMATCH"


def test_futures_short_passes():
    canonical = CanonicalOrderRequest(
        asset="BTC",
        direction="SHORT",
        order_type="MARKET",
        quantity=1,
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="I-1",
        snapshot_id="S-1",
        timestamp="2026-09-23T00:00:00+00:00",
    )
    provider = ProviderOrderRequest(
        venue="FUTURES",
        symbol="BTCUSDT",
        side="SELL",
        position_side="SHORT",
        order_type="MARKET",
        quantity="1",
        quantity_unit="CONTRACTS",
        entry_price=None,
        intent_id="I-1",
        snapshot_id="S-1",
        timestamp="2026-09-23T00:00:00+00:00",
    )
    result = build_provider_execution_binding(
        _eligibility(canonical),
        _handoff(provider),
    )
    assert result.status == BindingStatus.PASS


def test_provider_quantity_not_normalized():
    canonical = _canonical()
    provider = _provider()
    result = build_provider_execution_binding(
        _eligibility(canonical),
        _handoff(provider),
    )
    assert result.provider_request.quantity == 100
    assert result.provider_request.quantity_unit == "QUOTE_ASSET"


def run():
    tests = [
        test_requires_eligibility,
        test_requires_eligibility_pass,
        test_requires_handoff_pass,
        test_requires_preflight_pass,
        test_identity_mismatch_blocks,
        test_timestamp_mismatch_blocks,
        test_spot_long_passes_and_preserves_objects,
        test_spot_short_blocks,
        test_futures_short_passes,
        test_provider_quantity_not_normalized,
    ]
    for test in tests:
        test()
    print("CP46-F TESTS PASS: 10/10")


if __name__ == "__main__":
    run()
