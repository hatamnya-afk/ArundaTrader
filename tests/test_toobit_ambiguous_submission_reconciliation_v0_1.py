from toobit_ambiguous_submission_reconciliation_v0_1 import reconcile_ambiguous_submission

def test_found_order_never_allows_retry():
    row = {"clientOrderId": "INT-1", "orderId": "EX-1", "status": "NEW"}
    result = reconcile_ambiguous_submission(client_order_id="INT-1", open_orders=[row], recent_orders=[row])
    assert result["state"] == "FOUND"
    assert result["safe_to_retry"] is False

def test_absence_remains_unresolved():
    result = reconcile_ambiguous_submission(client_order_id="INT-1", open_orders=[], recent_orders=[])
    assert result["state"] == "NOT_FOUND_UNRESOLVED"
    assert result["safe_to_retry"] is False

def test_multiple_orders_conflict():
    result = reconcile_ambiguous_submission(
        client_order_id="INT-1",
        open_orders=[{"clientOrderId":"INT-1","orderId":"EX-1"}],
        recent_orders=[{"clientOrderId":"INT-1","orderId":"EX-2"}],
    )
    assert result["state"] == "CONFLICT"
    assert result["safe_to_retry"] is False

def test_invalid_rows_fail_closed():
    result = reconcile_ambiguous_submission(client_order_id="INT-1", open_orders=[None], recent_orders=[])
    assert result["state"] == "INVALID_OBSERVATION"
    assert result["safe_to_retry"] is False
