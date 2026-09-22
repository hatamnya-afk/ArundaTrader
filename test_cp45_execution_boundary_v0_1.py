from exchange_execution_boundary import execute_order
from exchange_execution_contract import (
    CanonicalOrderRequest,
    CanonicalExecutionResult,
)

class ForbiddenAdapter:
    def __init__(self):
        self.capabilities_called = False
        self.submit_called = False

    def capabilities(self):
        self.capabilities_called = True
        raise AssertionError("ADAPTER_CAPABILITIES_MUST_NOT_BE_CALLED")

    def submit_order(self, request):
        self.submit_called = True
        raise AssertionError("ADAPTER_SUBMIT_MUST_NOT_BE_CALLED")


def make_request():
    return CanonicalOrderRequest(
        asset="BTCUSDT",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100000,
        reference_price=None,
        intent_id="CP45-VERIFY-001",
        snapshot_id="CP45-SNAPSHOT-001",
        timestamp="2026-09-23T00:00:00",
    )


def test_execution_boundary_blocks_before_adapter_interaction():
    request = make_request()
    adapter = ForbiddenAdapter()

    result = execute_order(
        request=request,
        adapter=adapter,
    )

    assert isinstance(result, CanonicalExecutionResult)
    assert result.error_code == "EXECUTION_DISABLED"
    assert adapter.capabilities_called is False
    assert adapter.submit_called is False


def test_execution_boundary_preserves_request():
    request = make_request()
    original = request.quantity
    adapter = ForbiddenAdapter()

    result = execute_order(
        request=request,
        adapter=adapter,
    )

    assert result.error_code == "EXECUTION_DISABLED"
    assert request.quantity == original
    assert request.quantity == 1
    assert request.asset == "BTCUSDT"
    assert request.direction == "LONG"


def test_execution_boundary_is_fail_closed_without_adapter():
    request = make_request()

    result = execute_order(
        request=request,
        adapter=None,
    )

    assert isinstance(result, CanonicalExecutionResult)
    assert result.error_code == "EXECUTION_DISABLED"
