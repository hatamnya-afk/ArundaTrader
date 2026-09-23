from exchange_execution_contract import (
    CanonicalOrderRequest,
    CanonicalExecutionResult,
)
from toobit_trading_adapter import ToobitTradingAdapter


class ForbiddenSession:
    def get(self, *args, **kwargs):
        raise AssertionError("HTTP_GET_MUST_NOT_BE_CALLED")

    def post(self, *args, **kwargs):
        raise AssertionError("HTTP_POST_MUST_NOT_BE_CALLED")


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
        intent_id="CP46-A1-VERIFY-001",
        snapshot_id="CP46-A1-SNAPSHOT-001",
        timestamp="2026-09-23T00:00:00",
    )


def make_adapter():
    adapter = ToobitTradingAdapter()
    adapter.session = ForbiddenSession()
    return adapter


def test_canonical_submission_blocks_before_http():
    adapter = make_adapter()
    request = make_request()

    result = adapter.submit_order(request)

    assert isinstance(result, CanonicalExecutionResult)
    assert result.accepted is False
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "EXECUTION_DISABLED"
    assert result.exchange_order_id is None
    assert result.executed_quantity is None
    assert result.executed_price is None


def test_canonical_submission_preserves_quantity():
    adapter = make_adapter()
    request = make_request()

    original_quantity = request.quantity
    result = adapter.submit_order(request)

    assert result.error_code == "EXECUTION_DISABLED"
    assert request.quantity == original_quantity
    assert request.quantity == 1


def test_toobit_capability_does_not_enable_order_submission():
    adapter = make_adapter()

    capabilities = adapter.capabilities()

    assert capabilities.get("ORDER_SUBMISSION") is not True
    assert capabilities.get("ACCOUNT_READ") is True
    assert capabilities.get("BALANCE_READ") is True


def test_legacy_place_order_remains_blocked():
    adapter = make_adapter()

    result = adapter.place_order(
        {
            "asset": "BTCUSDT",
            "direction": "LONG",
            "quantity": 1,
        }
    )

    assert result.status == "BLOCKED"
    assert result.allowed is False
    assert "No exchange request is generated." in result.reason
