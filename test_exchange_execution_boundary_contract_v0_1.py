from __future__ import annotations

from dataclasses import replace

import exchange_execution_boundary as boundary
import exchange_execution_contract as contract


def _request(*, decision_id="DECISION-BIRTH-1"):
    return contract.CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity="0.01",
        quantity_unit=contract.QUANTITY_UNIT_BASE_ASSET,
        quantity_source=contract.QUANTITY_SOURCE_RISK_POSITION,
        entry_price="65000",
        reference_price="65000",
        intent_id="INTENT-1",
        snapshot_id="SNAPSHOT-1",
        timestamp="2026-10-10T00:00:00+00:00",
        decision_id=decision_id,
    )


def test_execution_disabled_result_preserves_authoritative_decision_id():
    request = _request()
    result = boundary.execute_order(request=request, adapter=object())

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "EXECUTION_DISABLED"
    assert result.decision_id == request.decision_id
    assert result.trade_event_id is None


def test_invalid_request_result_preserves_available_decision_id():
    request = replace(_request(), direction="INVALID")
    result = boundary.execute_order(request=request)

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "DIRECTION_INVALID"
    assert result.decision_id == request.decision_id
    assert result.trade_event_id is None


def test_execution_safety_flags_remain_disabled():
    assert contract.safety_contract() == {
        "EXECUTION_ENABLED": False,
        "ORDER_SUBMISSION_ENABLED": False,
        "ORDER_CANCELLATION_ENABLED": False,
        "WITHDRAWAL_ENABLED": False,
        "EXCHANGE_WRITE_ENABLED": False,
        "DATABASE_WRITE_ENABLED": False,
    }
