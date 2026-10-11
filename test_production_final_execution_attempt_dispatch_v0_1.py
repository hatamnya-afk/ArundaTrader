from unittest.mock import patch

from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from production_final_execution_attempt_dispatch_v0_1 import dispatch_final_execution_attempt


def _request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="intent-001",
        snapshot_id="snapshot-001",
        timestamp="2026-10-11T00:00:00+00:00",
        decision_id="decision-001",
    )


def _result():
    return CanonicalExecutionResult(
        accepted=False,
        exchange_order_id=None,
        status="FAIL_CLOSED",
        asset="BTC",
        direction="LONG",
        executed_quantity=None,
        executed_price=None,
        timestamp=None,
        adapter=None,
        error_code="TEST_RESULT",
        error_message="Controlled unit-test result.",
        decision_id="decision-001",
    )


def test_disabled_production_dispatch_stops_before_final_contract():
    with patch(
        "production_final_execution_attempt_dispatch_v0_1.run_final_execution_attempt_contract"
    ) as final_contract:
        result = dispatch_final_execution_attempt(
            request=_request(),
            execution_enabled=False,
        )

    assert result.error_code == "EXECUTION_DISABLED"
    assert result.decision_id == "decision-001"
    final_contract.assert_not_called()


def test_enabled_dispatch_fails_closed_when_required_context_is_missing():
    with patch(
        "production_final_execution_attempt_dispatch_v0_1.run_final_execution_attempt_contract"
    ) as final_contract:
        result = dispatch_final_execution_attempt(
            request=_request(),
            execution_enabled=True,
        )

    assert result.error_code == "FINAL_ATTEMPT_CONTEXT_INCOMPLETE"
    final_contract.assert_not_called()


def test_complete_enabled_dispatch_delegates_to_existing_final_contract():
    package = {"package_state": "EXECUTION_READY_PACKAGE"}
    mandate = {"decision": "AUTHORIZED"}
    adapter = object()
    expected = _result()
    with patch(
        "production_final_execution_attempt_dispatch_v0_1.run_final_execution_attempt_contract",
        return_value=expected,
    ) as final_contract:
        result = dispatch_final_execution_attempt(
            request=_request(),
            execution_enabled=True,
            execution_ready_package=package,
            management_observation=mandate,
            adapter=adapter,
            venue="SPOT",
            execution_instrument="BTC-USDT",
        )

    assert result is expected
    final_contract.assert_called_once_with(
        execution_ready_package=package,
        request=_request(),
        management_observation=mandate,
        adapter=adapter,
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
