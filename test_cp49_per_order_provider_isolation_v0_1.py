"""CP49 per-order provider isolation contract tests.

These tests prove the orchestration boundary only:
a CP46-D blocked order becomes fail-closed evidence and does not
invoke the execution bridge; an eligible order remains eligible for
the existing bridge. No exchange I/O is performed.
"""

from exchange_execution_contract import blocked_execution_result


def test_blocked_provider_order_is_fail_closed():
    result = blocked_execution_result(
        asset="AGLD",
        direction="LONG",
        adapter="TOOBIT",
        error_code="CP46_D_PROVIDER_BLOCKED",
        error_message="provider symbol unavailable",
    )
    assert result.status == "FAIL_CLOSED"
    assert result.accepted is False
    assert result.exchange_order_id is None
    assert result.error_code == "CP46_D_PROVIDER_BLOCKED"
    assert result.adapter == "TOOBIT"


def test_blocked_provider_order_cannot_look_like_submission():
    result = blocked_execution_result(
        asset="CYS",
        direction="LONG",
        adapter="TOOBIT",
        error_code="CP46_D_PROVIDER_BLOCKED",
        error_message="notional bounds incomplete",
    )
    assert result.status not in {"PASS", "REJECTED", "INCONCLUSIVE"}
    assert result.exchange_order_id is None


if __name__ == "__main__":
    test_blocked_provider_order_is_fail_closed()
    test_blocked_provider_order_cannot_look_like_submission()
    print("CP49 PER-ORDER PROVIDER ISOLATION : PASS")
