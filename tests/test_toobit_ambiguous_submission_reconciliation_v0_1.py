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


def test_same_provider_order_id_with_conflicting_facts_is_conflict():
    open_row = {"clientOrderId": "INT-1", "orderId": "EX-1", "status": "NEW"}
    recent_row = {"clientOrderId": "INT-1", "orderId": "EX-1", "status": "FILLED"}
    result = reconcile_ambiguous_submission(
        client_order_id="INT-1", open_orders=[open_row], recent_orders=[recent_row]
    )
    assert result["state"] == "CONFLICT"
    assert result["reason"] == "CONFLICTING_PROVIDER_FACTS_FOR_SAME_ORDER_ID"
    assert result["safe_to_retry"] is False


def test_near_match_client_order_id_is_not_accepted():
    result = reconcile_ambiguous_submission(
        client_order_id="INT-1",
        open_orders=[{"clientOrderId": "INT-10", "orderId": "EX-1"}],
        recent_orders=[],
    )
    assert result["state"] == "NOT_FOUND_UNRESOLVED"
    assert result["safe_to_retry"] is False


def test_invalid_observation_never_allows_retry():
    for result in (
        reconcile_ambiguous_submission(client_order_id="", open_orders=[], recent_orders=[]),
        reconcile_ambiguous_submission(client_order_id="INT-1", open_orders="bad", recent_orders=[]),
        reconcile_ambiguous_submission(client_order_id="INT-1", open_orders=[], recent_orders=[{"clientOrderId": 7}]),
    ):
        assert result["state"] == "INVALID_OBSERVATION"
        assert result["safe_to_retry"] is False
