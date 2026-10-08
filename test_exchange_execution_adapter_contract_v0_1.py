from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
    ExchangeExecutionAdapter,
    validate_adapter_contract,
)
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
)


class FakeAdapter:
    adapter_name = "FAKE_REPLACEABLE_ADAPTER"

    def capabilities(self):
        return ExchangeAdapterCapabilities(
            venue_discovery=True,
            instrument_resolution=True,
            constraint_read=True,
            account_read=True,
            order_state_read=True,
            order_submission=True,
            order_cancellation=True,
        )

    def prepare_order(self, request, *, venue, execution_instrument):
        return AdapterOrderPreparation(
            ready=True,
            reason="READY",
            adapter_name=self.adapter_name,
            venue=venue,
            request={"opaque": True},
        )

    def submit_prepared_order(self, preparation, *, canonical_request):
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="FAIL_CLOSED",
            asset=canonical_request.asset,
            direction=canonical_request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=None,
            adapter=self.adapter_name,
            error_code="EXECUTION_DISABLED",
            error_message="test adapter is not permitted to execute",
        )

    def submit_order(self, request):
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="FAIL_CLOSED",
            asset=request.asset,
            direction=request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=None,
            adapter=self.adapter_name,
            error_code="EXECUTION_DISABLED",
            error_message="test adapter is not permitted to execute",
        )

    def cancel_order(self, *, asset, exchange_order_id):
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=exchange_order_id,
            status="FAIL_CLOSED",
            asset=asset,
            direction=None,
            executed_quantity=None,
            executed_price=None,
            timestamp=None,
            adapter=self.adapter_name,
            error_code="EXECUTION_DISABLED",
            error_message="test adapter is not permitted to execute",
        )


def test_contract_is_provider_neutral():
    adapter = FakeAdapter()
    assert isinstance(adapter, ExchangeExecutionAdapter)
    assert validate_adapter_contract(adapter) == (True, "VALID")
    assert "TOOBIT" not in adapter.adapter_name


def test_missing_adapter_fails_closed():
    assert validate_adapter_contract(None) == (False, "ADAPTER_MISSING")


def test_structural_contract_does_not_call_provider():
    class ExplodingAdapter:
        adapter_name = "REPLACEABLE"

        def capabilities(self):
            raise AssertionError("provider call must not occur")

        def prepare_order(self, request, *, venue, execution_instrument):
            raise AssertionError("provider call must not occur")

        def submit_order(self, request):
            raise AssertionError("provider call must not occur")

        def cancel_order(self, *, asset, exchange_order_id):
            raise AssertionError("provider call must not occur")

    assert validate_adapter_contract(ExplodingAdapter()) == (True, "VALID")
