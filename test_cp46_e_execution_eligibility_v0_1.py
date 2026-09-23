"""
CP46-E — execution eligibility focused tests v0.1
"""

from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    build_execution_eligibility,
)
from cp46_d_provider_execution_handoff_v0_1 import (
    HandoffStatus,
    ProviderExecutionHandoffResult,
)
from exchange_execution_contract import CanonicalOrderRequest
from provider_order_translation_v0_1 import ProviderOrderRequest
from provider_preflight_v0_1 import (
    PreflightReason,
    PreflightStatus,
    ProviderPreflightResult,
)


def canonical():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=None,
        intent_id="I-1",
        snapshot_id="S-1",
        timestamp="2026-09-23T00:00:00+00:00",
    )


def provider():
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


def preflight(status=PreflightStatus.PASS):
    return ProviderPreflightResult(
        status=status,
        reason=(
            PreflightReason.PASS
            if status == PreflightStatus.PASS
            else PreflightReason.BLOCK_REQUEST_INVALID
        ),
        message="test",
    )


def handoff(status=HandoffStatus.PASS, pf=PreflightStatus.PASS):
    return ProviderExecutionHandoffResult(
        status=status,
        reason="test",
        message="test",
        provider_request=provider(),
        preflight=preflight(pf),
    )


def test_requires_canonical_request():
    result = build_execution_eligibility(None, handoff())
    assert result.status == EligibilityStatus.BLOCK
    assert result.reason == "CANONICAL_REQUEST_INVALID"


def test_requires_d_pass():
    result = build_execution_eligibility(canonical(), handoff(HandoffStatus.BLOCK))
    assert result.status == EligibilityStatus.BLOCK
    assert result.reason == "CP46_D_NOT_PASSED"


def test_requires_preflight_result():
    bad = ProviderExecutionHandoffResult(
        status=HandoffStatus.PASS,
        reason="test",
        message="test",
        provider_request=provider(),
        preflight=None,
    )
    result = build_execution_eligibility(canonical(), bad)
    assert result.status == EligibilityStatus.BLOCK
    assert result.reason == "PREFLIGHT_RESULT_MISSING"


def test_requires_preflight_pass():
    result = build_execution_eligibility(
        canonical(),
        handoff(HandoffStatus.PASS, PreflightStatus.BLOCK),
    )
    assert result.status == EligibilityStatus.BLOCK
    assert result.reason == "PREFLIGHT_NOT_PASSED"


def test_rejects_intent_mismatch():
    c = canonical()
    bad = ProviderOrderRequest(
        **{**provider().__dict__, "intent_id": "I-2"}
    )
    h = ProviderExecutionHandoffResult(
        status=HandoffStatus.PASS,
        reason="test",
        message="test",
        provider_request=bad,
        preflight=preflight(),
    )
    result = build_execution_eligibility(c, h)
    assert result.status == EligibilityStatus.BLOCK
    assert result.reason == "INTENT_ID_MISMATCH"


def test_rejects_snapshot_mismatch():
    c = canonical()
    bad = ProviderOrderRequest(
        **{**provider().__dict__, "snapshot_id": "S-2"}
    )
    h = ProviderExecutionHandoffResult(
        status=HandoffStatus.PASS,
        reason="test",
        message="test",
        provider_request=bad,
        preflight=preflight(),
    )
    result = build_execution_eligibility(c, h)
    assert result.status == EligibilityStatus.BLOCK
    assert result.reason == "SNAPSHOT_ID_MISMATCH"


def test_pass_preserves_canonical_request():
    c = canonical()
    result = build_execution_eligibility(c, handoff())
    assert result.status == EligibilityStatus.PASS
    assert result.reason == "PASS"
    assert result.canonical_request is c
    assert result.canonical_request.quantity == 1
    assert result.canonical_request.quantity_unit == "BASE_ASSET"


def run():
    tests = [
        test_requires_canonical_request,
        test_requires_d_pass,
        test_requires_preflight_result,
        test_requires_preflight_pass,
        test_rejects_intent_mismatch,
        test_rejects_snapshot_mismatch,
        test_pass_preserves_canonical_request,
    ]
    for test in tests:
        test()
    print("CP46-E TESTS PASS: 7/7")


if __name__ == "__main__":
    run()
