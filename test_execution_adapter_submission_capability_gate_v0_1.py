"""Read-only adapters must be rejected before any durable intent claim."""

import unittest

from exchange_execution_adapter_contract_v0_1 import ExchangeAdapterCapabilities
from exchange_execution_contract import CanonicalOrderRequest
from exchange_execution_order_attempt_boundary_v0_1 import attempt_prepared_order


class ReadOnlyAdapter:
    adapter_name = "READ_ONLY_FIXTURE"

    def __init__(self):
        self.prepare_calls = 0
        self.submit_calls = 0

    def capabilities(self):
        return ExchangeAdapterCapabilities(
            venue_discovery=True,
            instrument_resolution=True,
            constraint_read=True,
            account_read=True,
            order_state_read=True,
            order_submission=False,
            order_cancellation=False,
        )

    def prepare_order(self, request, *, venue, execution_instrument):
        self.prepare_calls += 1
        raise AssertionError("read-only adapter must be rejected before preparation")

    def submit_prepared_order(self, preparation, *, canonical_request):
        self.submit_calls += 1
        raise AssertionError("read-only adapter must never submit")

    def submit_order(self, request):
        self.submit_calls += 1
        raise AssertionError("read-only adapter must never submit")

    def cancel_order(self, *, asset, exchange_order_id):
        raise AssertionError("cancellation is not part of this test")


class ClaimStoreMustRemainUntouched:
    def __init__(self):
        self.claim_calls = 0
        self.transition_calls = 0

    def claim(self, **kwargs):
        self.claim_calls += 1
        raise AssertionError("unsupported adapter must not claim")

    def transition(self, **kwargs):
        self.transition_calls += 1
        raise AssertionError("unsupported adapter must not transition")


def test_read_only_adapter_is_blocked_before_claim_and_provider_call():
    request = CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="intent-readonly",
        snapshot_id="snapshot-readonly",
        timestamp="2026-10-15T00:00:00+00:00",
        decision_id="decision-readonly",
    )
    adapter = ReadOnlyAdapter()
    claim_store = ClaimStoreMustRemainUntouched()

    result = attempt_prepared_order(
        request=request,
        readiness_observation={},
        authorization_observation={},
        adapter=adapter,
        venue="SPOT",
        execution_instrument="BTC-USDT",
        claim_store=claim_store,
    )

    assert result.accepted is False
    assert result.error_code == "ADAPTER_ORDER_SUBMISSION_UNSUPPORTED"
    assert adapter.prepare_calls == 0
    assert adapter.submit_calls == 0
    assert claim_store.claim_calls == 0
    assert claim_store.transition_calls == 0


class ReadOnlyAdapterGateTests(unittest.TestCase):
    def test_read_only_adapter_is_blocked_before_claim_and_provider_call(self):
        test_read_only_adapter_is_blocked_before_claim_and_provider_call()


if __name__ == "__main__":
    unittest.main()
