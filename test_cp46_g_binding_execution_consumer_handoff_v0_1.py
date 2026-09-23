"""Focused CP46-G contract tests.

No network, exchange, database, or live execution is used.
"""

from __future__ import annotations

from types import SimpleNamespace

import cp46_g_binding_execution_consumer_handoff_v0_1 as g
from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from cp46_f_provider_execution_binding_v0_1 import (
    BindingStatus,
    ProviderExecutionBindingResult,
)
from exchange_execution_contract import CanonicalOrderRequest
from provider_order_translation_v0_1 import ProviderOrderRequest


def _canonical() -> CanonicalOrderRequest:
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="LIMIT",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="INTENT-1",
        snapshot_id="SNAP-1",
        timestamp="2026-09-23T00:00:00+00:00",
    )


def _provider() -> ProviderOrderRequest:
    return ProviderOrderRequest(
        venue="SPOT",
        symbol="BTCUSDT",
        side="BUY",
        position_side=None,
        order_type="LIMIT",
        quantity=1,
        quantity_unit="BASE_ASSET",
        entry_price=100,
        intent_id="INTENT-1",
        snapshot_id="SNAP-1",
        timestamp="2026-09-23T00:00:00+00:00",
    )


def _eligibility(canonical: CanonicalOrderRequest, status: str = "PASS"):
    return ExecutionEligibilityResult(
        status=status,
        reason="TEST",
        message="test",
        canonical_request=canonical if status == EligibilityStatus.PASS else None,
    )


def _binding(canonical: CanonicalOrderRequest, provider: ProviderOrderRequest, status: str = "PASS"):
    return ProviderExecutionBindingResult(
        status=status,
        reason="TEST",
        message="test",
        canonical_request=canonical if status == BindingStatus.PASS else None,
        provider_request=provider if status == BindingStatus.PASS else None,
    )


def test_pass_delegates_exact_canonical_and_original_eligibility(monkeypatch):
    canonical = _canonical()
    provider = _provider()
    eligibility = _eligibility(canonical)
    binding = _binding(canonical, provider)
    seen = {}

    def fake_execute_order(request, adapter=None, *, eligibility=None):
        seen["request"] = request
        seen["eligibility"] = eligibility
        seen["adapter"] = adapter
        return SimpleNamespace(status="BLOCKED", error_code="EXECUTION_DISABLED")

    monkeypatch.setattr(g, "execute_order", fake_execute_order)

    result = g.handoff_binding_to_execution_consumer(
        binding,
        eligibility,
        adapter="ADAPTER",
    )

    assert result.status == g.ConsumerHandoffStatus.PASS
    assert seen["request"] is canonical
    assert seen["eligibility"] is eligibility
    assert seen["adapter"] == "ADAPTER"
    assert result.canonical_request is canonical
    assert result.provider_request is provider


def test_binding_block_never_calls_execution_consumer(monkeypatch):
    canonical = _canonical()
    provider = _provider()
    eligibility = _eligibility(canonical)
    binding = _binding(canonical, provider, status=BindingStatus.BLOCK)

    def forbidden(*args, **kwargs):
        raise AssertionError("execution consumer must not be called")

    monkeypatch.setattr(g, "execute_order", forbidden)

    result = g.handoff_binding_to_execution_consumer(binding, eligibility)

    assert result.status == g.ConsumerHandoffStatus.BLOCK
    assert result.reason == "BINDING_NOT_PASS"


def test_missing_binding_blocks():
    result = g.handoff_binding_to_execution_consumer(
        None,
        _eligibility(_canonical()),
    )
    assert result.status == g.ConsumerHandoffStatus.BLOCK
    assert result.reason == "BINDING_INVALID"


def test_missing_eligibility_blocks():
    canonical = _canonical()
    result = g.handoff_binding_to_execution_consumer(
        _binding(canonical, _provider()),
        None,
    )
    assert result.status == g.ConsumerHandoffStatus.BLOCK
    assert result.reason == "ELIGIBILITY_INVALID"


def test_non_pass_eligibility_blocks_without_execution(monkeypatch):
    canonical = _canonical()
    binding = _binding(canonical, _provider())

    def forbidden(*args, **kwargs):
        raise AssertionError("execution consumer must not be called")

    monkeypatch.setattr(g, "execute_order", forbidden)

    result = g.handoff_binding_to_execution_consumer(
        binding,
        _eligibility(canonical, status=EligibilityStatus.BLOCK),
    )

    assert result.status == g.ConsumerHandoffStatus.BLOCK
    assert result.reason == "ELIGIBILITY_NOT_PASS"


def test_canonical_identity_mismatch_blocks(monkeypatch):
    canonical_a = _canonical()
    canonical_b = CanonicalOrderRequest(
        asset="ETH",
        direction="LONG",
        order_type="LIMIT",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="INTENT-2",
        snapshot_id="SNAP-2",
        timestamp="2026-09-23T00:00:00+00:00",
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("execution consumer must not be called")

    monkeypatch.setattr(g, "execute_order", forbidden)

    result = g.handoff_binding_to_execution_consumer(
        _binding(canonical_a, _provider()),
        _eligibility(canonical_b),
    )

    assert result.status == g.ConsumerHandoffStatus.BLOCK
    assert result.reason == "CANONICAL_IDENTITY_MISMATCH"


def test_provider_request_is_preserved_without_transformation(monkeypatch):
    canonical = _canonical()
    provider = _provider()
    eligibility = _eligibility(canonical)
    binding = _binding(canonical, provider)

    seen = {}

    def fake_execute_order(request, adapter=None, *, eligibility=None):
        seen["request"] = request
        return SimpleNamespace(status="BLOCKED")

    monkeypatch.setattr(g, "execute_order", fake_execute_order)

    result = g.handoff_binding_to_execution_consumer(
        binding,
        eligibility,
    )

    assert result.provider_request is provider
    assert provider.quantity == 1
    assert provider.quantity_unit == "BASE_ASSET"
    assert provider.symbol == "BTCUSDT"
    assert seen["request"] is canonical


def test_pass_does_not_claim_execution_success():
    canonical = _canonical()
    provider = _provider()
    eligibility = _eligibility(canonical)
    binding = _binding(canonical, provider)

    result = g.handoff_binding_to_execution_consumer(
        binding,
        eligibility,
    )

    assert result.status == g.ConsumerHandoffStatus.PASS
    assert result.execution_result is not None
    assert getattr(result.execution_result, "error_code", None) == "EXECUTION_DISABLED"
